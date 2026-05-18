"""
Seed script — creates 3 demo player accounts in Keycloak and fills the
database with realistic mock data spanning the last 90 days.

Run from repo root while the stack is up:
    python backend/seed.py
Or via run.sh:
    ./run.sh seed
"""

import os
import sys
import random
import requests
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

KC_URL   = os.environ.get("KEYCLOAK_URL", "http://localhost:8180")
KC_REALM = "sport-analytics"
DB_URL   = os.environ.get("DATABASE_URL", "postgresql://sa_user:sa_pass@localhost:5432/sportanalytics")

PLAYERS = [
    {"username": "player1", "email": "player1@demo.ro", "password": "player123",
     "position": "Midfielder", "height_cm": 178.0, "weight_kg": 74.5, "birth_year": 2000},
    {"username": "player2", "email": "player2@demo.ro", "password": "player123",
     "position": "Forward",    "height_cm": 182.0, "weight_kg": 78.0, "birth_year": 1998},
    {"username": "player3", "email": "player3@demo.ro", "password": "player123",
     "position": "Defender",   "height_cm": 185.5, "weight_kg": 83.0, "birth_year": 2001},
]

random.seed(42)


# ── Keycloak ───────────────────────────────────────────────────────────────

def admin_token():
    resp = requests.post(
        f"{KC_URL}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": "admin", "password": "admin123"},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"[KC] Admin auth failed: {resp.text}")
        sys.exit(1)
    return resp.json()["access_token"]


def ensure_kc_player(token, p):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base    = f"{KC_URL}/admin/realms/{KC_REALM}"

    existing = requests.get(
        f"{base}/users?username={p['username']}&exact=true",
        headers=headers, timeout=10,
    ).json()
    if existing:
        uid = existing[0]["id"]
        print(f"[KC] '{p['username']}' already exists  uid={uid}")
        return uid

    create_resp = requests.post(
        f"{base}/users",
        json={
            "username": p["username"], "email": p["email"],
            "firstName": p["username"].capitalize(), "lastName": "Demo",
            "enabled": True, "emailVerified": True, "requiredActions": [],
            "credentials": [{"type": "password", "value": p["password"], "temporary": False}],
        },
        headers=headers, timeout=10,
    )
    if create_resp.status_code not in (201, 204):
        print(f"[KC] Failed to create '{p['username']}': {create_resp.text}")
        return None

    uid = requests.get(
        f"{base}/users?username={p['username']}&exact=true",
        headers=headers, timeout=10,
    ).json()[0]["id"]

    role = requests.get(f"{base}/roles/player", headers=headers, timeout=10).json()
    requests.post(
        f"{base}/users/{uid}/role-mappings/realm",
        json=[role], headers=headers, timeout=10,
    )
    print(f"[KC] Created '{p['username']}'  uid={uid}")
    return uid


# ── DB seed ────────────────────────────────────────────────────────────────

def jitter(val, pct=0.15):
    return round(val * (1 + random.uniform(-pct, pct)), 2)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def seed_player(session, uid, p):
    from app.models import (
        PlayerProfile, TrainingLog, PhysicalAssessment, InjuryRecord, WellnessLog,
    )

    # Profile
    if not session.query(PlayerProfile).filter_by(user_id=uid).first():
        session.add(PlayerProfile(
            user_id=uid, username=p["username"],
            position=p["position"], height_cm=p["height_cm"],
            weight_kg=p["weight_kg"], birth_year=p["birth_year"],
        ))

    today = date.today()
    start = today - timedelta(days=89)

    # Training logs — every 2-4 days
    base_h = {"Midfielder": 1.8, "Forward": 2.0, "Defender": 1.6}[p["position"]]
    d = start
    while d <= today:
        if not session.query(TrainingLog).filter_by(user_id=uid, date=d).first():
            session.add(TrainingLog(
                user_id        = uid, date = d,
                training_hours = round(jitter(base_h, 0.25), 1),
                matches_played = random.choices([0, 1], weights=[4, 1])[0],
                notes          = random.choice([None, None, "Recovery", "Match prep", "Strength"]),
            ))
        d += timedelta(days=random.randint(2, 4))

    # Physical assessments — every ~2 weeks
    base_knee  = {"Midfielder": 82.0, "Forward": 79.0, "Defender": 88.0}[p["position"]]
    base_ham   = {"Midfielder": 70.0, "Forward": 72.0, "Defender": 68.0}[p["position"]]
    base_react = 240.0
    d = start
    while d <= today:
        if not session.query(PhysicalAssessment).filter_by(user_id=uid, date=d).first():
            session.add(PhysicalAssessment(
                user_id               = uid, date = d,
                knee_strength_score   = jitter(base_knee,  0.08),
                hamstring_flexibility = jitter(base_ham,   0.10),
                reaction_time_ms      = jitter(base_react, 0.10),
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
    base_cal = {"Midfielder": 2600, "Forward": 2800, "Defender": 2900}[p["position"]]
    d = start
    while d <= today:
        if not session.query(WellnessLog).filter_by(user_id=uid, date=d).first():
            cal   = int(jitter(base_cal, 0.12))
            prot  = round(cal * 0.28 / 4, 1)
            carbs = round(cal * 0.50 / 4, 1)
            fat   = round(cal * 0.22 / 9, 1)
            session.add(WellnessLog(
                user_id       = uid, date = d,
                calories      = cal, protein_g = prot, carbs_g = carbs, fat_g = fat,
                hydration_ml  = int(jitter(2400, 0.20)),
                sleep_hours   = round(jitter(7.2, 0.15), 1),
                sleep_quality = clamp(int(jitter(7, 0.20)), 1, 10),
                stress_level  = clamp(int(jitter(4, 0.30)), 1, 10),
                mood_score    = clamp(int(jitter(7, 0.20)), 1, 10),
            ))
        d += timedelta(days=random.randint(1, 3))

    session.commit()
    print(f"[DB] Seeded data for '{p['username']}'")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=== SportAnalytics seed ===\n")

    print("[1/2] Creating Keycloak player accounts...")
    token   = admin_token()
    uid_map = {}
    for p in PLAYERS:
        uid = ensure_kc_player(token, p)
        if uid:
            uid_map[p["username"]] = uid

    if not uid_map:
        print("No Keycloak users created — aborting.")
        sys.exit(1)

    print("\n[2/2] Seeding database...")
    from app import create_app
    from app.extensions import db
    from sqlalchemy.orm import sessionmaker

    app = create_app()
    with app.app_context():
        Session = sessionmaker(bind=db.engine)
        session = Session()
        for p in PLAYERS:
            uid = uid_map.get(p["username"])
            if uid:
                seed_player(session, uid, p)
        session.close()

    print("\n=== Done! ===")
    print("\nDemo accounts:")
    print("  coach_user  / coach123   (coach — sees all players)")
    print("  admin_user  / admin123   (admin)")
    for p in PLAYERS:
        print(f"  {p['username']:<10} / {p['password']}  ({p['position']})")


if __name__ == "__main__":
    main()
