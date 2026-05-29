import os
from datetime import date, datetime, timezone
import requests
from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import func
from models import db, PlayerProfile, TrainingLog, PhysicalAssessment, InjuryRecord, WellnessLog
from auth import require_auth

players_bp = Blueprint("players", __name__)


def _keycloak_url() -> str:
    return current_app.config["KEYCLOAK_URL"]

def _realm() -> str:
    return current_app.config["KEYCLOAK_REALM"]


def _admin_token() -> str:
    """Get an admin access token from the master realm."""
    resp = requests.post(
        f"{_keycloak_url()}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id":  "admin-cli",
            "username":   current_app.config["KEYCLOAK_ADMIN_USER"],
            "password":   current_app.config["KEYCLOAK_ADMIN_PASS"],
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Keycloak admin auth failed: {resp.text}")
    return resp.json()["access_token"]


def _fetch_user_club(user_id: str):
    """Fetch the 'club' attribute directly from Keycloak."""
    try:
        token   = _admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        base    = f"{_keycloak_url()}/admin/realms/{_realm()}"
        resp    = requests.get(f"{base}/users/{user_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            attrs = resp.json().get("attributes") or {}
            vals  = attrs.get("club") or []
            return vals[0] if vals else None
    except Exception:
        pass
    return None


def _notify_fl(club):
    if not club:
        return
    try:
        import requests as req
        FL_SERVICE = os.environ.get("FL_SERVICE_URL", "http://fl-service:5003")
        req.post(f"{FL_SERVICE}/internal/trigger", json={"club": club}, timeout=2)
    except Exception:
        pass


def _can_access(target_user_id: str) -> bool:
    claims = g.claims
    roles  = claims.get("realm_access", {}).get("roles", [])
    return claims.get("sub") == target_user_id or any(r in roles for r in ("coach", "admin"))


def _date_filter(query, model, from_str, to_str):
    if from_str:
        try:
            query = query.filter(model.date >= date.fromisoformat(from_str))
        except ValueError:
            pass
    if to_str:
        try:
            query = query.filter(model.date <= date.fromisoformat(to_str))
        except ValueError:
            pass
    return query


def compute_nutrition_score(calories, protein_g, carbs_g, fat_g, hydration_ml) -> float:
    """Derive a 0-100 Nutrition_Quality_Score from raw macro data."""
    score = 50.0
    if calories:
        if 2500 <= calories <= 3500:
            score += 15
        elif 2000 <= calories < 2500 or 3500 < calories <= 4000:
            score += 7
    if protein_g and protein_g >= 120:
        score += 15 if protein_g >= 150 else 8
    if hydration_ml:
        if hydration_ml >= 2500:
            score += 10
        elif hydration_ml >= 2000:
            score += 5
    if carbs_g and fat_g and protein_g:
        total_cals = protein_g * 4 + carbs_g * 4 + fat_g * 9
        if total_cals > 0:
            carb_pct = carbs_g * 4 / total_cals * 100
            if 45 <= carb_pct <= 65:
                score += 10
    return round(min(100.0, max(0.0, score)), 2)


# ── Players list ──────────────────────────────────────────────────

@players_bp.get("/")
@require_auth(roles=["coach", "admin"])
def list_players():
    claims     = g.claims
    roles      = claims.get("realm_access", {}).get("roles", [])
    is_admin   = "admin" in roles
    coach_club = None
    if not is_admin:
        coach_club = claims.get("club") or _fetch_user_club(claims.get("sub", ""))

    try:
        token   = _admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        base    = f"{current_app.config['KEYCLOAK_URL']}/admin/realms/{current_app.config['KEYCLOAK_REALM']}"
        users_resp = requests.get(
            f"{base}/roles/player/users?max=200",
            headers=headers, timeout=10,
        )
        kc_users = users_resp.json() if users_resp.status_code == 200 else []
    except Exception:
        kc_users = []

    profiles = {p.user_id: p for p in PlayerProfile.query.all()}

    result = []
    for u in kc_users:
        uid  = u.get("id")
        prof = profiles.get(uid)

        kc_club  = None
        kc_attrs = u.get("attributes") or {}
        if isinstance(kc_attrs.get("club"), list):
            kc_club = kc_attrs["club"][0]
        club = (prof.club if prof and prof.club else kc_club)

        if coach_club and club != coach_club:
            continue

        result.append({
            "user_id":  uid,
            "username": u.get("username"),
            "email":    u.get("email"),
            "club":     club,
            "profile":  prof.to_dict() if prof else None,
        })

    return jsonify(result)


# ── Biometrics ────────────────────────────────────────────────────

@players_bp.get("/<user_id>/biometrics")
@require_auth()
def get_biometrics(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    return jsonify(prof.to_dict() if prof else {})


@players_bp.put("/<user_id>/biometrics")
@require_auth()
def upsert_biometrics(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    if not prof:
        prof = PlayerProfile(user_id=user_id, username=data.get("username", user_id))
        db.session.add(prof)
    for field in ("username", "club", "position", "height_cm", "weight_kg", "birth_year"):
        if field in data:
            setattr(prof, field, data[field])
    prof.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(prof.to_dict())


# ── Training logs ─────────────────────────────────────────────────

@players_bp.get("/<user_id>/training")
@require_auth()
def get_training(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    q = TrainingLog.query.filter_by(user_id=user_id).order_by(TrainingLog.date)
    q = _date_filter(q, TrainingLog, request.args.get("from"), request.args.get("to"))
    return jsonify([r.to_dict() for r in q.all()])


@players_bp.post("/<user_id>/training")
@require_auth()
def add_training(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    try:
        entry = TrainingLog(
            user_id          = user_id,
            date             = date.fromisoformat(data["date"]),
            training_hours   = data.get("training_hours"),
            matches_played   = data.get("matches_played", 0),
            warmup_adherence = data.get("warmup_adherence"),
            notes            = data.get("notes"),
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    db.session.add(entry)
    db.session.commit()
    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    _notify_fl(prof.club if prof else None)
    return jsonify(entry.to_dict()), 201


@players_bp.delete("/<user_id>/training/<int:lid>")
@require_auth()
def delete_training(user_id, lid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    entry = TrainingLog.query.filter_by(id=lid, user_id=user_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": lid})


# ── Physical assessments ──────────────────────────────────────────

@players_bp.get("/<user_id>/physical")
@require_auth()
def get_physical(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    q = PhysicalAssessment.query.filter_by(user_id=user_id).order_by(PhysicalAssessment.date)
    q = _date_filter(q, PhysicalAssessment, request.args.get("from"), request.args.get("to"))
    return jsonify([r.to_dict() for r in q.all()])


@players_bp.post("/<user_id>/physical")
@require_auth()
def add_physical(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    try:
        entry = PhysicalAssessment(
            user_id               = user_id,
            date                  = date.fromisoformat(data["date"]),
            knee_strength_score   = data.get("knee_strength_score"),
            hamstring_flexibility = data.get("hamstring_flexibility"),
            reaction_time_ms      = data.get("reaction_time_ms"),
            balance_test_score    = data.get("balance_test_score"),
            sprint_speed_10m_s    = data.get("sprint_speed_10m_s"),
            agility_score         = data.get("agility_score"),
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    db.session.add(entry)
    db.session.commit()
    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    _notify_fl(prof.club if prof else None)
    return jsonify(entry.to_dict()), 201


@players_bp.delete("/<user_id>/physical/<int:aid>")
@require_auth()
def delete_physical(user_id, aid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    entry = PhysicalAssessment.query.filter_by(id=aid, user_id=user_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": aid})


# ── Injury records ────────────────────────────────────────────────

@players_bp.get("/<user_id>/injuries")
@require_auth()
def get_injuries(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    q = InjuryRecord.query.filter_by(user_id=user_id).order_by(InjuryRecord.date)
    q = _date_filter(q, InjuryRecord, request.args.get("from"), request.args.get("to"))
    return jsonify([r.to_dict() for r in q.all()])


@players_bp.post("/<user_id>/injuries")
@require_auth()
def add_injury(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    try:
        entry = InjuryRecord(
            user_id                = user_id,
            date                   = date.fromisoformat(data["date"]),
            injury_type            = data.get("injury_type"),
            injury_severity        = data.get("injury_severity"),
            rehabilitation_program = data.get("rehabilitation_program"),
            rehabilitation_weeks   = data.get("rehabilitation_weeks"),
            recurrence             = data.get("recurrence", False),
            notes                  = data.get("notes"),
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    db.session.add(entry)
    db.session.commit()
    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    _notify_fl(prof.club if prof else None)
    return jsonify(entry.to_dict()), 201


@players_bp.delete("/<user_id>/injuries/<int:rid>")
@require_auth()
def delete_injury(user_id, rid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    entry = InjuryRecord.query.filter_by(id=rid, user_id=user_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": rid})


# ── Wellness logs ─────────────────────────────────────────────────

@players_bp.get("/<user_id>/wellness")
@require_auth()
def get_wellness(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    q = WellnessLog.query.filter_by(user_id=user_id).order_by(WellnessLog.date)
    q = _date_filter(q, WellnessLog, request.args.get("from"), request.args.get("to"))
    return jsonify([r.to_dict() for r in q.all()])


@players_bp.post("/<user_id>/wellness")
@require_auth()
def add_wellness(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    try:
        cal  = data.get("calories")
        prot = data.get("protein_g")
        carb = data.get("carbs_g")
        fat  = data.get("fat_g")
        hyd  = data.get("hydration_ml")
        entry = WellnessLog(
            user_id         = user_id,
            date            = date.fromisoformat(data["date"]),
            calories        = cal,
            protein_g       = prot,
            carbs_g         = carb,
            fat_g           = fat,
            hydration_ml    = hyd,
            sleep_hours     = data.get("sleep_hours"),
            sleep_quality   = data.get("sleep_quality"),
            stress_level    = data.get("stress_level"),
            mood_score      = data.get("mood_score"),
            nutrition_score = compute_nutrition_score(cal, prot, carb, fat, hyd),
            notes           = data.get("notes"),
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    db.session.add(entry)
    db.session.commit()
    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    _notify_fl(prof.club if prof else None)
    return jsonify(entry.to_dict()), 201


@players_bp.delete("/<user_id>/wellness/<int:lid>")
@require_auth()
def delete_wellness(user_id, lid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    entry = WellnessLog.query.filter_by(id=lid, user_id=user_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": lid})
