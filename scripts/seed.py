"""
Seed script — creates demo accounts in Keycloak and populates the database
with realistic mock data spanning the last 90 days.

Clubs:
  FC Demo    — coach1   + player1 / player2 / player3
  FC Rivals  — coach2   + player4 / player5

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
    {"username": "coach1",  "email": "coach1@demo.ro",  "password": "coach123",
     "club": "FC Demo",    "role": "coach"},
    {"username": "coach2",  "email": "coach2@demo.ro",  "password": "coach123",
     "club": "FC Rivals",  "role": "coach"},
]

PLAYERS = [
    {"username": "player1", "email": "player1@demo.ro", "password": "player123",
     "club": "FC Demo",    "position": "Midfielder", "height_cm": 178.0, "weight_kg": 74.5, "birth_year": 2000},
    {"username": "player2", "email": "player2@demo.ro", "password": "player123",
     "club": "FC Demo",    "position": "Forward",    "height_cm": 182.0, "weight_kg": 78.0, "birth_year": 1998},
    {"username": "player3", "email": "player3@demo.ro", "password": "player123",
     "club": "FC Demo",    "position": "Defender",   "height_cm": 185.5, "weight_kg": 83.0, "birth_year": 2001},
    {"username": "player4", "email": "player4@demo.ro", "password": "player123",
     "club": "FC Rivals",  "position": "Forward",    "height_cm": 179.0, "weight_kg": 76.0, "birth_year": 1999},
    {"username": "player5", "email": "player5@demo.ro", "password": "player123",
     "club": "FC Rivals",  "position": "Goalkeeper", "height_cm": 191.0, "weight_kg": 88.0, "birth_year": 2002},
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
    pos = p["position"]

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
    d = start
    while d <= today:
        if not session.query(TrainingLog).filter_by(user_id=uid, date=d).first():
            session.add(TrainingLog(
                user_id=uid, date=d,
                training_hours=round(jitter(base_h, 0.25), 1),
                matches_played=random.choices([0, 1], weights=[4, 1])[0],
                warmup_adherence=round(random.uniform(0.5, 1.0), 2),
                notes=random.choice([None, None, "Recovery", "Match prep", "Strength"]),
            ))
        d += timedelta(days=random.randint(2, 4))

    # Physical assessments — every ~2 weeks
    base_knee  = {"Midfielder": 82.0, "Forward": 79.0, "Defender": 88.0, "Goalkeeper": 90.0}[pos]
    base_ham   = {"Midfielder": 70.0, "Forward": 72.0, "Defender": 68.0, "Goalkeeper": 65.0}[pos]
    d = start
    while d <= today:
        if not session.query(PhysicalAssessment).filter_by(user_id=uid, date=d).first():
            session.add(PhysicalAssessment(
                user_id=uid, date=d,
                knee_strength_score=jitter(base_knee, 0.08),
                hamstring_flexibility=jitter(base_ham, 0.10),
                reaction_time_ms=jitter(240.0, 0.10),
                balance_test_score=jitter(83.0, 0.08),
                sprint_speed_10m_s=jitter(5.9, 0.08),
                agility_score=jitter(78.0, 0.08),
            ))
        d += timedelta(days=random.randint(12, 16))

    # Injuries — 0-2 per player
    injury_pool = [
        ("Hamstring strain", "mild",     "RICE + physiotherapy", 2,  False),
        ("Ankle sprain",     "moderate", "Rest + physiotherapy", 4,  False),
        ("Knee ligament",    "severe",   "Surgery + physio",     12, True),
        ("Groin pull",       "mild",     "Rest + stretching",    1,  False),
        ("Calf strain",      "moderate", "Ice + physiotherapy",  3,  False),
    ]
    n_inj = random.randint(0, 2)
    for day_off in sorted(random.sample(range(5, 85), n_inj)):
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
                hydration_ml=int(jitter(2400, 0.20)),
                sleep_hours=round(jitter(7.2, 0.15), 1),
                sleep_quality=clamp(int(jitter(7, 0.20)), 1, 10),
                stress_level=clamp(int(jitter(4, 0.30)), 1, 10),
                mood_score=clamp(int(jitter(7, 0.20)), 1, 10),
            ))
        d += timedelta(days=random.randint(1, 3))

    session.commit()
    print(f"[DB] Seeded data for '{p['username']}'  ({p['club']})")


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
    print("  admin1   / admin123  — admin")
    print("  coach1   / coach123  — coach  — FC Demo")
    print("  coach2   / coach123  — coach  — FC Rivals")
    for p in PLAYERS:
        print(f"  {p['username']:<9} / {p['password']}  — player  — {p['club']}  ({p['position']})")


if __name__ == "__main__":
    main()
