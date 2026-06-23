"""
Demo script — aduce un jucător într-o zonă de risc de accidentare (SCĂZUT /
MEDIU / RIDICAT), pentru a demonstra live că pipeline-ul de Federated Learning
funcționează — fără salturi artificiale de la 0% la 100%.

Cum funcționează:
  - citește coeficienții + interceptul modelului global (fl_global_models);
  - alege ALEATOR o probabilitate-țintă în interiorul zonei cerute
    (ex. low ≈ 12-34%, medium ≈ 44-60%, high ≈ 70-90%);
  - pentru cele 11 caracteristici dinamice definește o extremă „bună" (risc
    minim) și una „rea" (risc maxim), în funcție de semnul coeficienților;
  - modelul fiind o regresie logistică pe caracteristici brute, scorul
    z = intercept + Σ coef·x este LINIAR în intensitatea t∈[0,1] care
    interpolează între cele două extreme, deci se rezolvă EXACT
    t = (logit(țintă) - z(0)) / (z(1) - z(0));
  - scrie în baza de date valorile interpolate la acel t (date fizice,
    wellness, antrenamente, accidentări);
  - cere riscul recalculat direct de la fl-service (același endpoint ca UI-ul)
    și afișează scorul ÎNAINTE și DUPĂ, alături de ținta aleasă.

Rulează cât timp stiva este pornită:
    ./run.sh risk high            # player1 -> o probabilitate aleatoare în zona high
    ./run.sh risk medium player6  # player6 -> zona medium
    ./run.sh risk low  player4    # player4 -> zona low
    ./run.sh risk reset player1   # revine la date realiste (profil seed)
"""

import argparse
import json
import math
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

import requests
from sqlalchemy import (create_engine, Column, Integer, String, Float,
                        Boolean, Date, Text, DateTime)
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_URL     = os.environ.get("DATABASE_URL",
             "postgresql://sa_user:sa_pass@localhost:5432/lawranalyzer")
FL_SERVICE = os.environ.get("FL_SERVICE_URL", "http://fl-service:5003")

# Ordinea EXACTĂ a caracteristicilor din fl/model.py
FEATURES = [
    "Position", "Previous_Injury_Count", "Knee_Strength_Score",
    "Hamstring_Flexibility", "Reaction_Time_ms", "Balance_Test_Score",
    "Sprint_Speed_10m_s", "Agility_Score", "Sleep_Hours_Per_Night",
    "Stress_Level_Score", "Nutrition_Quality_Score", "Warmup_Routine_Adherence",
]

# Codificarea pozițiilor, identică cu fl/model.py (LabelEncoder pe clasele sortate)
POSITION_CLASSES = ["Defender", "Forward", "Goalkeeper", "Midfielder"]

# Intervale realiste (lo, hi) pentru fiecare caracteristică dinamică
BOUNDS = {
    "Previous_Injury_Count":    (0, 6),
    "Knee_Strength_Score":      (40, 95),
    "Hamstring_Flexibility":    (45, 95),
    "Reaction_Time_ms":         (180, 360),
    "Balance_Test_Score":       (45, 98),
    "Sprint_Speed_10m_s":       (3.5, 9.5),
    "Agility_Score":            (40, 98),
    "Sleep_Hours_Per_Night":    (4.0, 9.0),
    "Stress_Level_Score":       (10, 95),
    "Nutrition_Quality_Score":  (25, 95),
    "Warmup_Routine_Adherence": (0.1, 1.0),
}

# Direcția „mai rău" (risc mai mare) folosită dacă modelul global lipsește.
# +1 = valoare mai mare înseamnă risc mai mare; -1 = valoare mai mică = risc mai mare.
WORSE_DIRECTION = {
    "Previous_Injury_Count":    +1,
    "Knee_Strength_Score":      -1,
    "Hamstring_Flexibility":    -1,
    "Reaction_Time_ms":         +1,
    "Balance_Test_Score":       -1,
    "Sprint_Speed_10m_s":       -1,
    "Agility_Score":            -1,
    "Sleep_Hours_Per_Night":    -1,
    "Stress_Level_Score":       +1,
    "Nutrition_Quality_Score":  -1,
    "Warmup_Routine_Adherence": -1,
}

# Probabilitatea-țintă este aleasă ALEATOR în interiorul acestor intervale,
# bine în interiorul pragurilor modelului (high≥0.65, medium≥0.40).
ZONE_TARGETS = {
    "low":    (0.12, 0.34),
    "medium": (0.44, 0.60),
    "high":   (0.70, 0.90),
}

# Profilul de risc folosit la seed (username -> profil), pentru modul "reset".
PROFILE_MAP = {
    "player1": "low",  "player2": "low",  "player3": "medium",
    "player4": "high", "player5": "high", "player6": "medium",
    "player7": "medium", "player8": "low", "player9": "high",
    "player10": "high", "player11": "high", "player12": "medium",
}

# Parametrii per-profil, identici cu seed.py
SEED_PROFILES = {
    "low":    dict(sleep=8.0, stress=3, warmup=(0.8, 1.0), injuries=(0, 1), phys=1.05),
    "medium": dict(sleep=7.2, stress=5, warmup=(0.5, 0.9), injuries=(1, 2), phys=1.00),
    "high":   dict(sleep=5.8, stress=8, warmup=(0.1, 0.5), injuries=(2, 3), phys=0.90),
}


def _jit(val, pct=0.12):
    return round(val * (1 + random.uniform(-pct, pct)), 2)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _sigmoid(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _logit(p):
    p = _clamp(p, 1e-6, 1.0 - 1e-6)
    return math.log(p / (1.0 - p))


# ── Modele standalone (fără Flask), ca în seed.py ──────────────────────────

class Base(DeclarativeBase):
    pass


class PlayerProfile(Base):
    __tablename__ = "player_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), unique=True, nullable=False)
    username = Column(String(64), nullable=False)
    club = Column(String(64))
    position = Column(String(32))
    height_cm = Column(Float); weight_kg = Column(Float); birth_year = Column(Integer)
    updated_at = Column(DateTime)


class TrainingLog(Base):
    __tablename__ = "training_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), nullable=False)
    date = Column(Date, nullable=False)
    training_hours = Column(Float); matches_played = Column(Integer)
    warmup_adherence = Column(Float); notes = Column(Text)


class PhysicalAssessment(Base):
    __tablename__ = "physical_assessments"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), nullable=False)
    date = Column(Date, nullable=False)
    knee_strength_score = Column(Float); hamstring_flexibility = Column(Float)
    reaction_time_ms = Column(Float); balance_test_score = Column(Float)
    sprint_speed_10m_s = Column(Float); agility_score = Column(Float)


class InjuryRecord(Base):
    __tablename__ = "injury_records"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), nullable=False)
    date = Column(Date, nullable=False)
    injury_type = Column(String(64)); injury_severity = Column(String(16))
    rehabilitation_program = Column(String(128)); rehabilitation_weeks = Column(Integer)
    recurrence = Column(Boolean); notes = Column(Text)


class WellnessLog(Base):
    __tablename__ = "wellness_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), nullable=False)
    date = Column(Date, nullable=False)
    calories = Column(Integer); protein_g = Column(Float); carbs_g = Column(Float)
    fat_g = Column(Float); hydration_ml = Column(Integer)
    sleep_hours = Column(Float); sleep_quality = Column(Integer)
    stress_level = Column(Integer); mood_score = Column(Integer)
    nutrition_score = Column(Float); notes = Column(Text)


class FLGlobalModel(Base):
    __tablename__ = "fl_global_models"
    id = Column(Integer, primary_key=True)
    round = Column(Integer)
    coef_json = Column(Text); intercept_json = Column(Text)
    accuracy = Column(Float); n_samples_total = Column(Integer)
    clubs_count = Column(Integer); updated_at = Column(DateTime)


# ── Helpers ────────────────────────────────────────────────────────────────

def fetch_risk(user_id: str):
    """Cere riscul recalculat de la fl-service (același endpoint ca UI-ul)."""
    try:
        r = requests.get(f"{FL_SERVICE}/internal/risk/{user_id}", timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception as exc:
        print(f"  [!] Nu am putut contacta fl-service: {exc}")
    return None


def position_code(prof) -> float:
    """Codifică poziția la fel ca fl/features.py (media setului = 1 dacă lipsește)."""
    pos = prof.position or ""
    if pos in POSITION_CLASSES:
        return float(POSITION_CLASSES.index(pos))
    return 1.0


def load_model(session):
    """Întoarce (dirs, coef, intercept).

    `dirs` = direcția care crește riscul pentru fiecare caracteristică dinamică.
    `coef`/`intercept` = None dacă nu există model global (caz în care nu se
    poate ținti analitic o probabilitate și se cade pe extreme)."""
    gm = session.query(FLGlobalModel).order_by(FLGlobalModel.id.desc()).first()
    if gm and gm.coef_json and gm.intercept_json:
        coef      = json.loads(gm.coef_json)[0]        # 12 ponderi
        intercept = json.loads(gm.intercept_json)[0]   # scalar
        dirs = {name: (1 if coef[i] >= 0 else -1)
                for i, name in enumerate(FEATURES) if name in BOUNDS}
        print(f"  Folosesc modelul global (rundă {gm.round}, {len(coef)} ponderi).")
        return dirs, coef, intercept
    print("  [!] Niciun model global găsit — folosesc direcțiile intuitive din domeniu.")
    return dict(WORSE_DIRECTION), None, None


def feature_value(name, t, dirs):
    """Valoarea caracteristicii la intensitatea t.
    t=0 -> extrema „bună" (risc minim); t=1 -> extrema „rea" (risc maxim)."""
    lo, hi = BOUNDS[name]
    worse  = dirs[name]
    good   = lo if worse > 0 else hi
    bad    = hi if worse > 0 else lo
    return good + (bad - good) * t


def _vector_at(t, dirs, pos):
    """Vectorul complet de 12 caracteristici la intensitatea t."""
    return [pos if name == "Position" else feature_value(name, t, dirs)
            for name in FEATURES]


def solve_t_for_probability(coef, intercept, dirs, pos, target_p):
    """Rezolvă EXACT intensitatea t pentru care modelul dă probabilitatea țintă.

    z(t) = intercept + Σ coef·x(t) este liniar în t (model logistic pe
    caracteristici brute), deci t = (logit(țintă) − z0) / (z1 − z0).
    Întoarce (t_clamped, p_min, p_max, a_fost_clampat)."""
    z0 = intercept + sum(c * x for c, x in zip(coef, _vector_at(0.0, dirs, pos)))
    z1 = intercept + sum(c * x for c, x in zip(coef, _vector_at(1.0, dirs, pos)))
    p_min, p_max = _sigmoid(z0), _sigmoid(z1)
    span = z1 - z0
    if abs(span) < 1e-9:
        return 0.5, p_min, p_max, True
    t_raw   = (_logit(target_p) - z0) / span
    clamped = t_raw < 0.0 or t_raw > 1.0
    return _clamp(t_raw, 0.0, 1.0), p_min, p_max, clamped


# ── Aplicarea modificărilor ────────────────────────────────────────────────

def _wipe(session, uid, start):
    """Șterge datele dinamice care formează vectorul de caracteristici curent."""
    session.query(WellnessLog).filter(
        WellnessLog.user_id == uid, WellnessLog.date >= start).delete(synchronize_session=False)
    session.query(TrainingLog).filter(
        TrainingLog.user_id == uid, TrainingLog.date >= start).delete(synchronize_session=False)
    session.query(PhysicalAssessment).filter(
        PhysicalAssessment.user_id == uid).delete(synchronize_session=False)
    session.query(InjuryRecord).filter(
        InjuryRecord.user_id == uid).delete(synchronize_session=False)


def write_features(session, uid, t, dirs):
    """Scrie în DB datele care produc vectorul de caracteristici la intensitatea t."""
    val = {name: feature_value(name, t, dirs) for name in BOUNDS}
    high_flavor    = t >= 0.5
    good_nutrition = val["Nutrition_Quality_Score"] >= 60

    today = date.today()
    start = today - timedelta(days=84)

    # 1) Curăță datele dinamice recente
    _wipe(session, uid, start)

    # 2) Evaluare fizică (se folosește cea mai recentă) — datată azi
    session.add(PhysicalAssessment(
        user_id=uid, date=today,
        knee_strength_score=round(val["Knee_Strength_Score"], 1),
        hamstring_flexibility=round(val["Hamstring_Flexibility"], 1),
        reaction_time_ms=round(val["Reaction_Time_ms"], 1),
        balance_test_score=round(val["Balance_Test_Score"], 1),
        sprint_speed_10m_s=round(val["Sprint_Speed_10m_s"], 2),
        agility_score=round(val["Agility_Score"], 1),
    ))

    # 3) Accidentări (contează numărul) — distribuite în ultimele 84 de zile
    n_inj = int(round(val["Previous_Injury_Count"]))
    inj_pool = [
        ("Hamstring strain", "mild", "RICE + physiotherapy", 2),
        ("Ankle sprain", "moderate", "Rest + physiotherapy", 4),
        ("Knee ligament", "severe", "Surgery + physio", 12),
        ("Calf strain", "moderate", "Ice + physiotherapy", 3),
        ("Groin pull", "mild", "Rest + stretching", 1),
        ("Shin splints", "mild", "Rest + ice", 2),
    ]
    for k in range(n_inj):
        ty, sev, prog, weeks = inj_pool[k % len(inj_pool)]
        session.add(InjuryRecord(
            user_id=uid, date=start + timedelta(days=7 + k * 12),
            injury_type=ty, injury_severity=sev,
            rehabilitation_program=prog, rehabilitation_weeks=weeks, recurrence=(k > 0),
        ))

    # 4) Wellness (medie pe 90 de zile) — ~9 intrări cu valorile-țintă
    cal = 2800 if good_nutrition else 1700
    d = start
    while d <= today:
        session.add(WellnessLog(
            user_id=uid, date=d,
            calories=cal,
            protein_g=round(cal * (0.28 if good_nutrition else 0.15) / 4, 1),
            carbs_g=round(cal * 0.50 / 4, 1),
            fat_g=round(cal * (0.22 if good_nutrition else 0.32) / 9, 1),
            hydration_ml=2800 if good_nutrition else 1500,
            sleep_hours=round(val["Sleep_Hours_Per_Night"], 1),
            sleep_quality=8 if val["Sleep_Hours_Per_Night"] >= 7 else 4,
            stress_level=int(round(val["Stress_Level_Score"])),
            mood_score=4 if high_flavor else 7,
            nutrition_score=round(val["Nutrition_Quality_Score"], 1),
        ))
        d += timedelta(days=10)

    # 5) Antrenamente (medie warmup pe 90 de zile) — ~9 intrări
    d = start
    while d <= today:
        session.add(TrainingLog(
            user_id=uid, date=d,
            training_hours=2.2 if high_flavor else 1.6,   # supraantrenament în zona high
            matches_played=0,
            warmup_adherence=round(val["Warmup_Routine_Adherence"], 2),
        ))
        d += timedelta(days=10)

    session.commit()
    return val


def run_targeted(session, prof, mode):
    """Aduce jucătorul la o probabilitate aleatoare din zona `mode` (low/medium/high)."""
    uid = prof.user_id
    dirs, coef, intercept = load_model(session)

    lo_p, hi_p = ZONE_TARGETS[mode]
    target = random.uniform(lo_p, hi_p)
    print(f"  Probabilitate-țintă aleasă în zona {mode.upper()}: {target * 100:.1f}%")

    if coef is not None:
        pos = position_code(prof)
        t, p_min, p_max, clamped = solve_t_for_probability(coef, intercept, dirs, pos, target)
        print(f"  Interval realizabil pentru acest jucător: "
              f"{p_min * 100:.1f}% – {p_max * 100:.1f}%")
        if clamped:
            print("  [!] Ținta iese din intervalul modelului — folosesc cea mai apropiată valoare.")
        print(f"  Intensitate calculată: t = {t:.3f}  (0 = risc minim, 1 = risc maxim)")
    else:
        # Fără model: cad pe extreme / mijloc
        t = {"high": 1.0, "low": 0.0, "medium": 0.5}[mode]

    val = write_features(session, uid, t, dirs)
    return val, target


def apply_seed_like(session, prof, profile):
    """Regenerează date realiste, jitterate, ca în seed.py (după profilul de risc)."""
    uid = prof.user_id
    pos = prof.position or "Midfielder"
    cfg = SEED_PROFILES.get(profile, SEED_PROFILES["medium"])

    today = date.today()
    start = today - timedelta(days=89)
    _wipe(session, uid, start)

    # Antrenamente — la fiecare 2-4 zile
    base_h = {"Midfielder": 1.8, "Forward": 2.0, "Defender": 1.6, "Goalkeeper": 1.5}.get(pos, 1.8)
    if profile == "high":
        base_h *= 1.3
    d = start
    while d <= today:
        session.add(TrainingLog(
            user_id=uid, date=d,
            training_hours=round(_jit(base_h, 0.25), 1),
            matches_played=random.choices([0, 1], weights=[4, 1])[0],
            warmup_adherence=round(random.uniform(*cfg["warmup"]), 2),
        ))
        d += timedelta(days=random.randint(2, 4))

    # Evaluări fizice — la fiecare ~2 săptămâni
    base_knee = {"Midfielder": 82.0, "Forward": 79.0, "Defender": 88.0, "Goalkeeper": 90.0}.get(pos, 82.0)
    base_ham  = {"Midfielder": 70.0, "Forward": 72.0, "Defender": 68.0, "Goalkeeper": 65.0}.get(pos, 70.0)
    m = cfg["phys"]
    d = start
    while d <= today:
        session.add(PhysicalAssessment(
            user_id=uid, date=d,
            knee_strength_score=_jit(base_knee * m, 0.08),
            hamstring_flexibility=_jit(base_ham * m, 0.10),
            reaction_time_ms=_jit(240.0 / m, 0.10),
            balance_test_score=_jit(83.0 * m, 0.08),
            sprint_speed_10m_s=_jit(5.9 * m, 0.08),
            agility_score=_jit(78.0 * m, 0.08),
        ))
        d += timedelta(days=random.randint(12, 16))

    # Accidentări — număr după profil
    inj_pool = [
        ("Hamstring strain", "mild", "RICE + physiotherapy", 2, False),
        ("Ankle sprain", "moderate", "Rest + physiotherapy", 4, False),
        ("Knee ligament", "severe", "Surgery + physio", 12, True),
        ("Calf strain", "moderate", "Ice + physiotherapy", 3, False),
    ]
    lo, hi = cfg["injuries"]
    n_inj = random.randint(lo, hi)
    for off in (sorted(random.sample(range(5, 85), n_inj)) if n_inj else []):
        ty, sev, prog, weeks, recur = random.choice(inj_pool)
        session.add(InjuryRecord(
            user_id=uid, date=start + timedelta(days=off),
            injury_type=ty, injury_severity=sev,
            rehabilitation_program=prog, rehabilitation_weeks=weeks, recurrence=recur,
        ))

    # Wellness — la fiecare 1-3 zile (nutrition_score rămâne NULL, ca în seed)
    base_cal = {"Midfielder": 2600, "Forward": 2800, "Defender": 2900, "Goalkeeper": 2700}.get(pos, 2600)
    d = start
    while d <= today:
        cal = int(_jit(base_cal, 0.12))
        session.add(WellnessLog(
            user_id=uid, date=d,
            calories=cal,
            protein_g=round(cal * 0.28 / 4, 1),
            carbs_g=round(cal * 0.50 / 4, 1),
            fat_g=round(cal * 0.22 / 9, 1),
            hydration_ml=int(_jit(2400 if profile != "high" else 1800, 0.20)),
            sleep_hours=round(_jit(cfg["sleep"], 0.10), 1),
            sleep_quality=_clamp(int(_jit(8 if profile == "low" else 5 if profile == "high" else 7, 0.20)), 1, 10),
            stress_level=_clamp(int(_jit(cfg["stress"], 0.25)), 1, 10),
            mood_score=_clamp(int(_jit(8 if profile == "low" else 5 if profile == "high" else 7, 0.20)), 1, 10),
        ))
        d += timedelta(days=random.randint(1, 3))

    session.commit()


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Demo: aduce un jucător în zona low/medium/high sau reset")
    ap.add_argument("mode", choices=["high", "medium", "low", "reset"],
                    help="low/medium/high = țintește o probabilitate aleatoare din zonă; "
                         "reset = date realiste (ca seed)")
    ap.add_argument("--player", default="player1", help="username-ul jucătorului (implicit player1)")
    ap.add_argument("--user-id", default=None, help="user_id direct (ocolește căutarea după username)")
    args = ap.parse_args()

    engine = create_engine(DB_URL)
    session = sessionmaker(bind=engine)()

    # Rezolvă jucătorul
    if args.user_id:
        prof = session.query(PlayerProfile).filter_by(user_id=args.user_id).first()
    else:
        prof = session.query(PlayerProfile).filter_by(username=args.player).first()
    if not prof:
        print(f"[x] Jucătorul '{args.user_id or args.player}' nu există în baza de date. "
              f"Rulează mai întâi ./run.sh seed")
        sys.exit(1)

    uid = prof.user_id
    print("=" * 60)
    print(f" Demo risc — {prof.username}  ({prof.club or 'fără club'}, {prof.position or '?'})")
    if args.mode == "reset":
        print(" Acțiune: resetare la date realiste (profil seed)")
    else:
        print(f" Țintă: zona {args.mode.upper()}")
    print("=" * 60)

    before = fetch_risk(uid)
    if before:
        print(f"\n  ÎNAINTE:  risc = {before['risk'].upper():6}  "
              f"(probabilitate {before['probability'] * 100:.1f}%)")

    print("\n  Aplic modificările...")
    target = None
    if args.mode == "reset":
        profile = PROFILE_MAP.get(prof.username, "medium")
        apply_seed_like(session, prof, profile)
        print(f"  Date realiste regenerate (profil seed: {profile}).")
    else:
        val, target = run_targeted(session, prof, args.mode)
        print("  Vector de caracteristici aplicat:")
        for name, v in val.items():
            print(f"    - {name:26} = {round(v, 2)}")

    after = fetch_risk(uid)
    if after:
        line = (f"\n  DUPĂ:     risc = {after['risk'].upper():6}  "
                f"(probabilitate {after['probability'] * 100:.1f}%)")
        if target is not None:
            line += f"   [țintă {target * 100:.1f}%]"
        print(line)

    session.close()
    print("\n  Gata. Reîncarcă pagina de recomandări / clasamentul de risc în UI.")
    print("=" * 60)


if __name__ == "__main__":
    main()
