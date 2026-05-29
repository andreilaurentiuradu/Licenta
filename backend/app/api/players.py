from datetime import date, datetime, timezone, timedelta
import json
import logging
import requests
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func
from app.extensions import db
from app.models import PlayerProfile, TrainingLog, PhysicalAssessment, InjuryRecord, WellnessLog
from app.api.keycloak_auth import keycloak_required, _admin_token, _fetch_user_club
from fl.features import compute_nutrition_score

log = logging.getLogger(__name__)

players_bp = Blueprint("players", __name__)


def _fl_trigger(user_id: str):
    """Schedule an FL update for the club of user_id (fire-and-forget)."""
    try:
        prof = PlayerProfile.query.filter_by(user_id=user_id).first()
        club = prof.club if prof else None
        if club:
            from fl.pipeline import trigger_fl_update
            trigger_fl_update(club, current_app._get_current_object())
    except Exception as exc:
        log.debug("[FL] Trigger skipped: %s", exc)


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
    claims    = request.kc_claims
    roles     = claims.get("realm_access", {}).get("roles", [])
    is_admin  = "admin" in roles
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

        # Resolve club: prefer DB profile, fall back to Keycloak attribute
        kc_club = None
        kc_attrs = u.get("attributes") or {}
        if isinstance(kc_attrs.get("club"), list):
            kc_club = kc_attrs["club"][0]
        club = (prof.club if prof and prof.club else kc_club)

        # Coach: only see players from their own club
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
    for field in ("username", "club", "position", "height_cm", "weight_kg", "birth_year"):
        if field in data:
            setattr(prof, field, data[field])
    prof.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(prof.to_dict())


# ── Recommendations ───────────────────────────────────────────────

def _collect_player_context(user_id: str) -> dict:
    """Aggregate recent player data into a dict for the AI prompt."""
    today   = date.today()
    last_30 = today - timedelta(days=30)
    last_90 = today - timedelta(days=90)

    prof = PlayerProfile.query.filter_by(user_id=user_id).first()

    w = db.session.query(
        func.avg(WellnessLog.sleep_hours).label("sleep"),
        func.avg(WellnessLog.sleep_quality).label("sleep_q"),
        func.avg(WellnessLog.stress_level).label("stress"),
        func.avg(WellnessLog.mood_score).label("mood"),
        func.avg(WellnessLog.calories).label("calories"),
        func.avg(WellnessLog.hydration_ml).label("hydration"),
    ).filter(WellnessLog.user_id == user_id, WellnessLog.date >= last_30).first()

    t = db.session.query(
        func.coalesce(func.sum(TrainingLog.training_hours), 0).label("hours"),
        func.coalesce(func.sum(TrainingLog.matches_played), 0).label("matches"),
        func.count(TrainingLog.id).label("sessions"),
    ).filter(TrainingLog.user_id == user_id, TrainingLog.date >= last_30).first()

    phys = (PhysicalAssessment.query
            .filter_by(user_id=user_id)
            .order_by(PhysicalAssessment.date.desc())
            .first())

    recent_inj = (InjuryRecord.query
                  .filter(InjuryRecord.user_id == user_id, InjuryRecord.date >= last_90)
                  .all())
    total_inj  = InjuryRecord.query.filter_by(user_id=user_id).count()

    return {
        "position":   (prof.club and prof.position) or "Unknown",
        "birth_year": prof.birth_year if prof else None,
        "wellness": {
            "avg_sleep_hours":   round(w.sleep   or 0, 1),
            "avg_sleep_quality": round(w.sleep_q or 0, 1),
            "avg_stress":        round(w.stress  or 0, 1),
            "avg_mood":          round(w.mood    or 0, 1),
            "avg_calories":      round(w.calories  or 0),
            "avg_hydration_ml":  round(w.hydration or 0),
        },
        "training": {
            "total_hours": round(float(t.hours), 1),
            "sessions":    t.sessions,
            "matches":     t.matches,
        },
        "physical": phys.to_dict() if phys else {},
        "recent_injuries": [
            {"type": i.injury_type, "severity": i.injury_severity}
            for i in recent_inj
        ],
        "total_injuries": total_inj,
    }


_SYSTEM_PROMPT = """You are a professional sports performance analyst and physiotherapist.
Analyse the player metrics provided and return a JSON object with this exact structure:
{
  "injury_risk": "low" | "medium" | "high",
  "recommendations": [
    {
      "category": string,
      "priority": "high" | "medium" | "low",
      "text": string
    }
  ]
}
Rules:
- Return 3 to 4 recommendations.
- Categories must be one of: Injury Prevention, Training Load, Wellness, Nutrition, Recovery.
- Each recommendation must be specific to the player's data — not generic advice.
- The "text" field must be 1–2 concise, actionable sentences.
- Return only valid JSON — no markdown, no extra keys."""


def _call_openai(ctx: dict) -> dict | None:
    api_key = current_app.config.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

        inj_lines = "\n".join(
            f"  - {i['type']} ({i['severity']})" for i in ctx["recent_injuries"]
        ) or "  None"

        user_msg = f"""Player data:
Position: {ctx['position']}
Birth year: {ctx['birth_year'] or 'Unknown'}

Wellness — last 30 days average:
  Sleep: {ctx['wellness']['avg_sleep_hours']}h  Quality: {ctx['wellness']['avg_sleep_quality']}/10
  Stress: {ctx['wellness']['avg_stress']}/10  Mood: {ctx['wellness']['avg_mood']}/10
  Calories: {ctx['wellness']['avg_calories']} kcal  Hydration: {ctx['wellness']['avg_hydration_ml']} ml

Training — last 30 days:
  {ctx['training']['total_hours']}h across {ctx['training']['sessions']} sessions, {ctx['training']['matches']} matches

Latest physical assessment:
  Knee strength: {ctx['physical'].get('knee_strength_score', 'N/A')}
  Hamstring flexibility: {ctx['physical'].get('hamstring_flexibility', 'N/A')}
  Reaction time: {ctx['physical'].get('reaction_time_ms', 'N/A')} ms

Injuries:
  Total on record: {ctx['total_injuries']}
  Last 90 days:
{inj_lines}"""

        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.4,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as exc:
        log.warning("OpenAI call failed: %s", exc)
        return None


_DEFAULT_RECOMMENDATIONS = {
    "injury_risk": "low",
    "recommendations": [
        {
            "category": "Injury Prevention",
            "priority": "high",
            "text": "Prioritise hamstring flexibility and knee strength exercises. Consistent warm-up routines significantly reduce ligament injury risk.",
        },
        {
            "category": "Training Load",
            "priority": "medium",
            "text": "Maintain current training intensity and add one recovery session per week to manage cumulative fatigue.",
        },
        {
            "category": "Wellness",
            "priority": "low",
            "text": "Sleep and stress metrics are within normal range. Monitor hydration closely on match days.",
        },
    ],
}


@players_bp.get("/<user_id>/recommendations")
@keycloak_required()
def get_recommendations(user_id):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403

    ctx = _collect_player_context(user_id)
    ai  = _call_openai(ctx)

    if ai:
        payload = {
            "injury_risk":     ai.get("injury_risk", "low"),
            "last_updated":    datetime.now(timezone.utc).isoformat(),
            "recommendations": ai.get("recommendations", []),
            "ai_generated":    True,
            "note": "Generated by AI based on your recent metrics.",
        }
    else:
        payload = {
            **_DEFAULT_RECOMMENDATIONS,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "ai_generated": False,
            "note": "AI key not configured — showing default recommendations. Set GROQ_API_KEY to enable personalised insights.",
        }

    return jsonify(payload)


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
    _fl_trigger(user_id)
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
            balance_test_score    = data.get("balance_test_score"),
            sprint_speed_10m_s    = data.get("sprint_speed_10m_s"),
            agility_score         = data.get("agility_score"),
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    db.session.add(entry)
    db.session.commit()
    _fl_trigger(user_id)
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
    _fl_trigger(user_id)
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
    _fl_trigger(user_id)
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
