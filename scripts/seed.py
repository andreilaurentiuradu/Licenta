"""
Seed script — creates demo accounts in Keycloak and populates the database
with realistic mock data spanning the last 90 days.

4 clubs x 3 players — designed to demonstrate the FL pipeline:
  each club has a distinct risk profile so FedAvg aggregates meaningfully.

  FC Demo    — coach1  — low injury risk   (good sleep, low stress, high warmup)
  FC Rivals  — coach2  — high injury risk  (poor sleep, high stress, low warmup)
  FC United  — coach3  — medium risk       (mixed profile)
  FC Alpha   — coach4  — high injury count (overtraining pattern)

Run while the stack is up:
    ./run.sh seed
"""

import os
import sys
import random
import time
import requests
from datetime import date, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text, DateTime
from datetime import datetime, timezone

KC_URL   = os.environ.get("KEYCLOAK_URL", "http://localhost:8180")
KC_REALM = "lawranalyzer"
DB_URL   = os.environ.get("DATABASE_URL",
           "postgresql://sa_user:sa_pass@localhost:5432/lawranalyzer")

COACHES = [
    {"username": "coach1", "email": "coach1@demo.ro", "password": "coach123",
     "club": "FC Demo",   "role": "coach"},
    {"username": "coach2", "email": "coach2@demo.ro", "password": "coach123",
     "club": "FC Rivals", "role": "coach"},
    {"username": "coach3", "email": "coach3@demo.ro", "password": "coach123",
     "club": "FC United", "role": "coach"},
    {"username": "coach4", "email": "coach4@demo.ro", "password": "coach123",
     "club": "FC Alpha",  "role": "coach"},
]

# risk_profile controls injury probability and wellness quality:
#   "low"    — 0-1 injuries, good sleep/stress, high warmup adherence
#   "medium" — 1-2 injuries, average wellness
#   "high"   — 2-3 injuries, poor sleep, high stress, low warmup

PLAYERS = [
    # FC Demo — low injury risk
    {"username": "player1",  "email": "player1@demo.ro",  "password": "player123",
     "club": "FC Demo",   "position": "Midfielder", "height_cm": 178.0, "weight_kg": 74.5,
     "birth_year": 2000,  "risk_profile": "low"},
    {"username": "player2",  "email": "player2@demo.ro",  "password": "player123",
     "club": "FC Demo",   "position": "Forward",    "height_cm": 182.0, "weight_kg": 78.0,
     "birth_year": 1998,  "risk_profile": "low"},
    {"username": "player3",  "email": "player3@demo.ro",  "password": "player123",
     "club": "FC Demo",   "position": "Defender",   "height_cm": 185.5, "weight_kg": 83.0,
     "birth_year": 2001,  "risk_profile": "medium"},

    # FC Rivals — high injury risk
    {"username": "player4",  "email": "player4@demo.ro",  "password": "player123",
     "club": "FC Rivals", "position": "Forward",    "height_cm": 179.0, "weight_kg": 76.0,
     "birth_year": 1999,  "risk_profile": "high"},
    {"username": "player5",  "email": "player5@demo.ro",  "password": "player123",
     "club": "FC Rivals", "position": "Goalkeeper", "height_cm": 191.0, "weight_kg": 88.0,
     "birth_year": 2002,  "risk_profile": "high"},
    {"username": "player6",  "email": "player6@demo.ro",  "password": "player123",
     "club": "FC Rivals", "position": "Midfielder", "height_cm": 175.0, "weight_kg": 71.0,
     "birth_year": 2000,  "risk_profile": "medium"},

    # FC United — medium / mixed risk
    {"username": "player7",  "email": "player7@demo.ro",  "password": "player123",
     "club": "FC United", "position": "Defender",   "height_cm": 183.0, "weight_kg": 80.0,
     "birth_year": 1997,  "risk_profile": "medium"},
    {"username": "player8",  "email": "player8@demo.ro",  "password": "player123",
     "club": "FC United", "position": "Forward",    "height_cm": 177.0, "weight_kg": 73.0,
     "birth_year": 2001,  "risk_profile": "low"},
    {"username": "player9",  "email": "player9@demo.ro",  "password": "player123",
     "club": "FC United", "position": "Goalkeeper", "height_cm": 189.0, "weight_kg": 85.0,
     "birth_year": 1999,  "risk_profile": "high"},

    # FC Alpha — high injury count (overtraining)
    {"username": "player10", "email": "player10@demo.ro", "password": "player123",
     "club": "FC Alpha",  "position": "Midfielder", "height_cm": 176.0, "weight_kg": 72.0,
     "birth_year": 2000,  "risk_profile": "high"},
    {"username": "player11", "email": "player11@demo.ro", "password": "player123",
     "club": "FC Alpha",  "position": "Forward",    "height_cm": 181.0, "weight_kg": 77.0,
     "birth_year": 1998,  "risk_profile": "high"},
    {"username": "player12", "email": "player12@demo.ro", "password": "player123",
     "club": "FC Alpha",  "position": "Defender",   "height_cm": 184.0, "weight_kg": 81.0,
     "birth_year": 2002,  "risk_profile": "medium"},
]

random.seed(42)


# ── SQLAlchemy models (standalone, no Flask) ───────────────────────────────

class Base(DeclarativeBase):
    pass


class PlayerProfile(Base):
    __tablename__ = "player_profiles"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(String(36), unique=True, nullable=False)
    username   = Column(String(64), nullable=False)
    club       = Column(String(64))
    position   = Column(String(32))
    height_cm  = Column(Float)
    weight_kg  = Column(Float)
    birth_year = Column(Integer)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TrainingLog(Base):
    __tablename__ = "training_logs"
    id               = Column(Integer, primary_key=True)
    user_id          = Column(String(36), nullable=False)
    date             = Column(Date, nullable=False)
    training_hours   = Column(Float)
    matches_played   = Column(Integer, default=0)
    warmup_adherence = Column(Float)
    notes            = Column(Text)


class PhysicalAssessment(Base):
    __tablename__ = "physical_assessments"
    id                    = Column(Integer, primary_key=True)
    user_id               = Column(String(36), nullable=False)
    date                  = Column(Date, nullable=False)
    knee_strength_score   = Column(Float)
    hamstring_flexibility = Column(Float)
    reaction_time_ms      = Column(Float)
    balance_test_score    = Column(Float)
    sprint_speed_10m_s    = Column(Float)
    agility_score         = Column(Float)


class InjuryRecord(Base):
    __tablename__ = "injury_records"
    id                     = Column(Integer, primary_key=True)
    user_id                = Column(String(36), nullable=False)
    date                   = Column(Date, nullable=False)
    injury_type            = Column(String(64))
    injury_severity        = Column(String(16))
    rehabilitation_program = Column(String(128))
    rehabilitation_weeks   = Column(Integer)
    recurrence             = Column(Boolean, default=False)
    notes                  = Column(Text)


class WellnessLog(Base):
    __tablename__ = "wellness_logs"
    id              = Column(Integer, primary_key=True)
    user_id         = Column(String(36), nullable=False)
    date            = Column(Date, nullable=False)
    calories        = Column(Integer)
    protein_g       = Column(Float)
    carbs_g         = Column(Float)
    fat_g           = Column(Float)
    hydration_ml    = Column(Integer)
    sleep_hours     = Column(Float)
    sleep_quality   = Column(Integer)
    stress_level    = Column(Integer)
    mood_score      = Column(Integer)
    nutrition_score = Column(Float)
    notes           = Column(Text)


# ── Keycloak helpers ───────────────────────────────────────────────────────

def admin_token(retries=20, delay=6):
    url = f"{KC_URL}/realms/master/protocol/openid-connect/token"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                url,
                data={"grant_type": "password", "client_id": "admin-cli",
                      "username": "admin", "password": "admin123"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()["access_token"]
            print(f"[KC] Attempt {attempt}/{retries}: HTTP {resp.status_code} — retrying in {delay}s…")
        except Exception as exc:
            print(f"[KC] Attempt {attempt}/{retries}: {exc.__class__.__name__} — retrying in {delay}s…")
        if attempt < retries:
            time.sleep(delay)
    print("[KC] Keycloak did not become ready in time.")
    sys.exit(1)


def ensure_kc_user(token, u):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base    = f"{KC_URL}/admin/realms/{KC_REALM}"

    existing = requests.get(
        f"{base}/users?username={u['username']}&exact=true",
        headers=headers, timeout=10,
    ).json()
    if existing:
        uid = existing[0]["id"]
        print(f"[KC] '{u['username']}' already exists  uid={uid}")
        return uid

    body = {
        "username":    u["username"],
        "email":       u["email"],
        "firstName":   u["username"].capitalize(),
        "lastName":    "Demo",
        "enabled":     True,
        "emailVerified": True,
        "requiredActions": [],
        "credentials": [{"type": "password", "value": u["password"], "temporary": False}],
        "attributes":  {"club": [u["club"]]},
    }
    resp = requests.post(f"{base}/users", json=body, headers=headers, timeout=10)
    if resp.status_code not in (201, 204):
        print(f"[KC] Failed to create '{u['username']}': {resp.text}")
        return None

    uid  = requests.get(
        f"{base}/users?username={u['username']}&exact=true",
        headers=headers, timeout=10,
    ).json()[0]["id"]

    role_name = u.get("role", "player")
    role = requests.get(f"{base}/roles/{role_name}", headers=headers, timeout=10).json()
    requests.post(
        f"{base}/users/{uid}/role-mappings/realm",
        json=[role], headers=headers, timeout=10,
    )
    print(f"[KC] Created '{u['username']}'  uid={uid}  role={role_name}  club={u['club']}")
    return uid


# ── DB seed helpers ────────────────────────────────────────────────────────

def jitter(val, pct=0.15):
    return round(val * (1 + random.uniform(-pct, pct)), 2)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def seed_player(session, uid, p):
    pos     = p["position"]
    profile = p.get("risk_profile", "medium")

    # Per-profile parameters
    PROFILES = {
        #                sleep   stress  warmup  n_inj_range  phys_mult
        "low":    dict(sleep=8.0, stress=3,  warmup=(0.8, 1.0), injuries=(0, 1), phys=1.05),
        "medium": dict(sleep=7.2, stress=5,  warmup=(0.5, 0.9), injuries=(1, 2), phys=1.00),
        "high":   dict(sleep=5.8, stress=8,  warmup=(0.1, 0.5), injuries=(2, 3), phys=0.90),
    }
    cfg = PROFILES[profile]

    prof = session.query(PlayerProfile).filter_by(user_id=uid).first()
    if not prof:
        session.add(PlayerProfile(
            user_id=uid, username=p["username"], club=p["club"],
            position=pos, height_cm=p["height_cm"],
            weight_kg=p["weight_kg"], birth_year=p["birth_year"],
        ))
    elif prof.club != p["club"]:
        prof.club = p["club"]

    today = date.today()
    start = today - timedelta(days=89)

    # Training logs — every 2-4 days
    base_h = {"Midfielder": 1.8, "Forward": 2.0, "Defender": 1.6, "Goalkeeper": 1.5}[pos]
    if profile == "high":
        base_h *= 1.3  # overtraining pattern
    d = start
    while d <= today:
        if not session.query(TrainingLog).filter_by(user_id=uid, date=d).first():
            session.add(TrainingLog(
                user_id=uid, date=d,
                training_hours=round(jitter(base_h, 0.25), 1),
                matches_played=random.choices([0, 1], weights=[4, 1])[0],
                warmup_adherence=round(random.uniform(*cfg["warmup"]), 2),
                notes=random.choice([None, None, "Recovery", "Match prep", "Strength"]),
            ))
        d += timedelta(days=random.randint(2, 4))

    # Physical assessments — every ~2 weeks
    base_knee = {"Midfielder": 82.0, "Forward": 79.0, "Defender": 88.0, "Goalkeeper": 90.0}[pos]
    base_ham  = {"Midfielder": 70.0, "Forward": 72.0, "Defender": 68.0, "Goalkeeper": 65.0}[pos]
    d = start
    while d <= today:
        if not session.query(PhysicalAssessment).filter_by(user_id=uid, date=d).first():
            m = cfg["phys"]
            session.add(PhysicalAssessment(
                user_id=uid, date=d,
                knee_strength_score=jitter(base_knee * m, 0.08),
                hamstring_flexibility=jitter(base_ham * m, 0.10),
                reaction_time_ms=jitter(240.0 / m, 0.10),
                balance_test_score=jitter(83.0 * m, 0.08),
                sprint_speed_10m_s=jitter(5.9 * m, 0.08),
                agility_score=jitter(78.0 * m, 0.08),
            ))
        d += timedelta(days=random.randint(12, 16))

    # Injuries — count driven by risk profile
    injury_pool = [
        ("Hamstring strain", "mild",     "RICE + physiotherapy", 2,  False),
        ("Ankle sprain",     "moderate", "Rest + physiotherapy", 4,  False),
        ("Knee ligament",    "severe",   "Surgery + physio",     12, True),
        ("Groin pull",       "mild",     "Rest + stretching",    1,  False),
        ("Calf strain",      "moderate", "Ice + physiotherapy",  3,  False),
        ("Shin splints",     "mild",     "Rest + ice",           2,  False),
    ]
    lo, hi = cfg["injuries"]
    n_inj = random.randint(lo, hi)
    if n_inj > 0:
        for day_off in sorted(random.sample(range(5, 85), min(n_inj, 80))):
            inj_date = start + timedelta(days=day_off)
            if not session.query(InjuryRecord).filter_by(user_id=uid, date=inj_date).first():
                t, sev, prog, weeks, recur = random.choice(injury_pool)
                session.add(InjuryRecord(
                    user_id=uid, date=inj_date,
                    injury_type=t, injury_severity=sev,
                    rehabilitation_program=prog, rehabilitation_weeks=weeks,
                    recurrence=recur,
                ))

    # Wellness logs — every 1-3 days
    base_cal = {"Midfielder": 2600, "Forward": 2800, "Defender": 2900, "Goalkeeper": 2700}[pos]
    d = start
    while d <= today:
        if not session.query(WellnessLog).filter_by(user_id=uid, date=d).first():
            cal   = int(jitter(base_cal, 0.12))
            prot  = round(cal * 0.28 / 4, 1)
            carbs = round(cal * 0.50 / 4, 1)
            fat   = round(cal * 0.22 / 9, 1)
            session.add(WellnessLog(
                user_id=uid, date=d,
                calories=cal, protein_g=prot, carbs_g=carbs, fat_g=fat,
                hydration_ml=int(jitter(2400 if profile != "high" else 1800, 0.20)),
                sleep_hours=round(jitter(cfg["sleep"], 0.10), 1),
                sleep_quality=clamp(int(jitter(8 if profile == "low" else 5 if profile == "high" else 7, 0.20)), 1, 10),
                stress_level=clamp(int(jitter(cfg["stress"], 0.25)), 1, 10),
                mood_score=clamp(int(jitter(8 if profile == "low" else 5 if profile == "high" else 7, 0.20)), 1, 10),
            ))
        d += timedelta(days=random.randint(1, 3))

    session.commit()
    print(f"[DB] Seeded '{p['username']}'  ({p['club']})  profile={profile}")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=== LawrAnalyzer seed ===\n")

    print("[1/2] Creating Keycloak accounts...")
    token = admin_token()

    uid_map = {}
    for c in COACHES:
        uid = ensure_kc_user(token, c)
        if uid:
            uid_map[c["username"]] = uid

    for p in PLAYERS:
        uid = ensure_kc_user(token, {**p, "role": "player"})
        if uid:
            uid_map[p["username"]] = uid

    print("\n[2/2] Seeding database...")
    engine  = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    for p in PLAYERS:
        uid = uid_map.get(p["username"])
        if uid:
            seed_player(session, uid, p)

    session.close()

    print("\n=== Done! ===")
    print("\nDemo accounts:")
    print("  admin1    / admin123  — admin")
    print()
    clubs = {}
    for p in PLAYERS:
        clubs.setdefault(p["club"], []).append(p)
    for c in COACHES:
        print(f"  {c['username']:<9} / coach123   — coach  — {c['club']}")
        for p in clubs.get(c["club"], []):
            print(f"  {p['username']:<9} / player123  — player — {c['club']}  ({p['position']}, risk={p['risk_profile']})")
        print()


if __name__ == "__main__":
    main()
