from datetime import date, datetime, timezone
import requests
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models import PlayerProfile, TrainingLog, PhysicalAssessment, InjuryRecord, WellnessLog
from app.api.keycloak_auth import keycloak_required, _admin_token

players_bp = Blueprint("players", __name__)


def _can_access(target_user_id: str) -> bool:
    claims = request.kc_claims
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


# ── Players list ──────────────────────────────────────────────────

@players_bp.get("/")
@keycloak_required(roles=["coach", "admin"])
def list_players():
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
        result.append({
            "user_id":  uid,
            "username": u.get("username"),
            "email":    u.get("email"),
            "profile":  prof.to_dict() if prof else None,
        })
    return jsonify(result)


# ── Biometrics ────────────────────────────────────────────────────

@players_bp.get("/<user_id>/biometrics")
@keycloak_required()
def get_biometrics(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    return jsonify(prof.to_dict() if prof else {})


@players_bp.put("/<user_id>/biometrics")
@keycloak_required()
def upsert_biometrics(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    if not prof:
        prof = PlayerProfile(user_id=user_id, username=data.get("username", user_id))
        db.session.add(prof)
    for field in ("username", "position", "height_cm", "weight_kg", "birth_year"):
        if field in data:
            setattr(prof, field, data[field])
    prof.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(prof.to_dict())


# ── Training logs ─────────────────────────────────────────────────

@players_bp.get("/<user_id>/training")
@keycloak_required()
def get_training(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    q = TrainingLog.query.filter_by(user_id=user_id).order_by(TrainingLog.date)
    q = _date_filter(q, TrainingLog, request.args.get("from"), request.args.get("to"))
    return jsonify([r.to_dict() for r in q.all()])


@players_bp.post("/<user_id>/training")
@keycloak_required()
def add_training(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    try:
        entry = TrainingLog(
            user_id        = user_id,
            date           = date.fromisoformat(data["date"]),
            training_hours = data.get("training_hours"),
            matches_played = data.get("matches_played", 0),
            notes          = data.get("notes"),
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@players_bp.delete("/<user_id>/training/<int:lid>")
@keycloak_required()
def delete_training(user_id, lid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    entry = TrainingLog.query.filter_by(id=lid, user_id=user_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": lid})


# ── Physical assessments ──────────────────────────────────────────

@players_bp.get("/<user_id>/physical")
@keycloak_required()
def get_physical(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    q = PhysicalAssessment.query.filter_by(user_id=user_id).order_by(PhysicalAssessment.date)
    q = _date_filter(q, PhysicalAssessment, request.args.get("from"), request.args.get("to"))
    return jsonify([r.to_dict() for r in q.all()])


@players_bp.post("/<user_id>/physical")
@keycloak_required()
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
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@players_bp.delete("/<user_id>/physical/<int:aid>")
@keycloak_required()
def delete_physical(user_id, aid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    entry = PhysicalAssessment.query.filter_by(id=aid, user_id=user_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": aid})


# ── Injury records ────────────────────────────────────────────────

@players_bp.get("/<user_id>/injuries")
@keycloak_required()
def get_injuries(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    q = InjuryRecord.query.filter_by(user_id=user_id).order_by(InjuryRecord.date)
    q = _date_filter(q, InjuryRecord, request.args.get("from"), request.args.get("to"))
    return jsonify([r.to_dict() for r in q.all()])


@players_bp.post("/<user_id>/injuries")
@keycloak_required()
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
    return jsonify(entry.to_dict()), 201


@players_bp.delete("/<user_id>/injuries/<int:rid>")
@keycloak_required()
def delete_injury(user_id, rid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    entry = InjuryRecord.query.filter_by(id=rid, user_id=user_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": rid})


# ── Wellness logs ─────────────────────────────────────────────────

@players_bp.get("/<user_id>/wellness")
@keycloak_required()
def get_wellness(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    q = WellnessLog.query.filter_by(user_id=user_id).order_by(WellnessLog.date)
    q = _date_filter(q, WellnessLog, request.args.get("from"), request.args.get("to"))
    return jsonify([r.to_dict() for r in q.all()])


@players_bp.post("/<user_id>/wellness")
@keycloak_required()
def add_wellness(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    try:
        entry = WellnessLog(
            user_id       = user_id,
            date          = date.fromisoformat(data["date"]),
            calories      = data.get("calories"),
            protein_g     = data.get("protein_g"),
            carbs_g       = data.get("carbs_g"),
            fat_g         = data.get("fat_g"),
            hydration_ml  = data.get("hydration_ml"),
            sleep_hours   = data.get("sleep_hours"),
            sleep_quality = data.get("sleep_quality"),
            stress_level  = data.get("stress_level"),
            mood_score    = data.get("mood_score"),
            notes         = data.get("notes"),
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@players_bp.delete("/<user_id>/wellness/<int:lid>")
@keycloak_required()
def delete_wellness(user_id, lid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    entry = WellnessLog.query.filter_by(id=lid, user_id=user_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": lid})
