import json
import logging
from datetime import date, datetime, timezone, timedelta

from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import func

from models import db, PlayerProfile, TrainingLog, PhysicalAssessment, InjuryRecord, WellnessLog
from auth import require_auth

ai_bp = Blueprint("ai", __name__)
log   = logging.getLogger(__name__)


def _can_access(target_user_id: str) -> bool:
    claims = g.claims
    roles  = claims.get("realm_access", {}).get("roles", [])
    return claims.get("sub") == target_user_id or any(r in roles for r in ("coach", "admin"))


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
- The "text" field must be 1-2 concise, actionable sentences.
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


@ai_bp.get("/<user_id>/recommendations")
@require_auth()
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
