import json
import logging
import os
from datetime import date, timedelta

import requests as req
from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import func

from models import (
    db, PlayerProfile, TrainingLog, PhysicalAssessment,
    InjuryRecord, WellnessLog, Recommendation,
)
from auth import require_auth

ai_bp = Blueprint("ai", __name__)
log   = logging.getLogger(__name__)

_FL_SERVICE = os.environ.get("FL_SERVICE_URL", "http://fl-service:5003")

CATEGORIES = ["Injury Prevention", "Training Load", "Wellness", "Nutrition", "Recovery"]


def _fetch_fl_risk(user_id: str) -> dict:
    """Fetch FL model injury risk for a player from fl-service (internal endpoint)."""
    try:
        resp = req.get(f"{_FL_SERVICE}/internal/risk/{user_id}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        log.debug("[ai] FL risk fetch failed for %s: %s", user_id, exc)
    return {"risk": "low", "probability": 0.0}


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
        "position":   (prof.position if prof else None) or "Unknown",
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


def _player_block(ctx: dict) -> str:
    """Render the player-data block shared by all prompts."""
    inj_lines = "\n".join(
        f"  - {i['type']} ({i['severity']})" for i in ctx["recent_injuries"]
    ) or "  None"
    fl_risk = ctx.get("fl_risk", {})
    return f"""Player data:
Position: {ctx['position']}
Birth year: {ctx['birth_year'] or 'Unknown'}
Injury risk (Federated Learning model): {fl_risk.get('risk', 'unknown').upper()} ({fl_risk.get('probability', 0) * 100:.0f}% probability)

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


_SYSTEM_PROMPT = """You are a professional sports performance analyst and physiotherapist.
Analyse the player metrics provided and return a JSON object with this exact structure:
{
  "recommendations": [
    { "category": string, "priority": "high" | "medium" | "low", "text": string }
  ]
}
Rules:
- Return 3 to 4 recommendations.
- Categories must be one of: Injury Prevention, Training Load, Wellness, Nutrition, Recovery.
- Each recommendation must be specific to the player's data — not generic advice.
- The injury risk level is provided to you — tailor the urgency accordingly.
- The "text" field must be 1-2 concise, actionable sentences.
- Return only valid JSON — no markdown, no extra keys."""

_SYSTEM_PROMPT_ONE = """You are a professional sports performance analyst and physiotherapist.
Return a JSON object with this exact structure:
{ "category": string, "priority": "high" | "medium" | "low", "text": string }
Rules:
- Generate exactly ONE recommendation in the requested category.
- It must be specific to the player's data and must NOT repeat any of the texts to avoid.
- The "text" field must be 1-2 concise, actionable sentences.
- Return only valid JSON — no markdown, no extra keys."""


def _openai_client():
    api_key = current_app.config.get("GROQ_API_KEY", "")
    if not api_key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def _call_openai(ctx: dict) -> dict | None:
    """Generate the full set of recommendations (returns dict with 'recommendations')."""
    client = _openai_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": _player_block(ctx)},
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.4,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as exc:
        log.warning("OpenAI call failed: %s", exc)
        return None


def _call_openai_one(ctx: dict, category: str, avoid_texts: list) -> dict | None:
    """Generate ONE recommendation in a given category, avoiding listed texts."""
    client = _openai_client()
    if client is None:
        return None
    try:
        avoid = "\n".join(f"  - {t}" for t in avoid_texts) or "  (none)"
        user_msg = f"Requested category: {category}\n\nTexts to avoid (do not repeat):\n{avoid}\n\n{_player_block(ctx)}"
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT_ONE},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0.5,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as exc:
        log.warning("OpenAI single-category call failed: %s", exc)
        return None


# Fallback pool used when the LLM is unavailable (no GROQ_API_KEY or error).
_DEFAULT_POOL = {
    "Injury Prevention": [
        "Prioritise hamstring flexibility and knee strength exercises; consistent warm-ups reduce ligament injury risk.",
        "Add eccentric hamstring work (Nordic curls) twice a week to lower soft-tissue injury risk.",
        "Include ankle stability and balance drills to protect against recurrent sprains.",
    ],
    "Training Load": [
        "Maintain current training intensity and add one recovery session per week to manage cumulative fatigue.",
        "Avoid sudden spikes in weekly load; increase volume gradually (around 10% per week).",
        "Alternate high- and low-intensity days to keep the acute-to-chronic workload ratio in a safe range.",
    ],
    "Wellness": [
        "Sleep and stress metrics are within range; monitor hydration closely on match days.",
        "Aim for 7-9 hours of sleep consistently — poor sleep is associated with higher injury risk.",
        "Track stress before competitions and use breathing or relaxation routines when it is elevated.",
    ],
    "Nutrition": [
        "Ensure adequate protein intake (around 1.6-2.0 g/kg) to support muscle recovery.",
        "Align carbohydrate intake with training volume to sustain energy and recovery.",
        "Plan structured meals around training sessions rather than eating opportunistically.",
    ],
    "Recovery": [
        "Add an active recovery session (light mobility, stretching) after intense match days.",
        "Use post-training cooldowns and adequate hydration to speed up recovery.",
        "Schedule at least one full rest day per week to allow tissue adaptation.",
    ],
}


def _generate_set(user_id: str, fl_risk: dict) -> list:
    """Produce an initial set of recommendations (LLM, or default pool fallback)."""
    ctx = _collect_player_context(user_id)
    ctx["fl_risk"] = fl_risk
    ai = _call_openai(ctx)
    if ai and ai.get("recommendations"):
        out = []
        for r in ai["recommendations"]:
            if r.get("text"):
                out.append({
                    "category": r.get("category", "Wellness"),
                    "priority": r.get("priority", "medium"),
                    "text":     r["text"],
                })
        if out:
            return out
    # fallback: one from each of three categories
    return [
        {"category": "Injury Prevention", "priority": "high",   "text": _DEFAULT_POOL["Injury Prevention"][0]},
        {"category": "Training Load",     "priority": "medium", "text": _DEFAULT_POOL["Training Load"][0]},
        {"category": "Wellness",          "priority": "low",    "text": _DEFAULT_POOL["Wellness"][0]},
    ]


def _generate_one(user_id: str, category: str, avoid_texts: list, fl_risk: dict) -> dict:
    """Produce ONE replacement recommendation in `category`, avoiding `avoid_texts`."""
    ctx = _collect_player_context(user_id)
    ctx["fl_risk"] = fl_risk
    one = _call_openai_one(ctx, category, avoid_texts)
    if one and one.get("text") and one["text"] not in avoid_texts:
        return {"category": category, "priority": one.get("priority", "medium"), "text": one["text"]}
    # fallback: next unused text from the pool
    for t in _DEFAULT_POOL.get(category, []):
        if t not in avoid_texts:
            return {"category": category, "priority": "medium", "text": t}
    return {
        "category": category,
        "priority": "low",
        "text": "Continue monitoring this area and consult your coaching staff for tailored guidance.",
    }


def _active_query(user_id: str):
    return Recommendation.query.filter_by(user_id=user_id).filter(
        Recommendation.status.in_(("pending", "accepted")))


def _serialize(user_id: str, fl_risk: dict) -> dict:
    active = _active_query(user_id).order_by(Recommendation.id).all()
    completed = (Recommendation.query
                 .filter_by(user_id=user_id, status="completed")
                 .order_by(Recommendation.updated_at.desc())
                 .all())
    return {
        "injury_risk":    fl_risk["risk"],          # FL model — authoritative, not the LLM
        "fl_probability": fl_risk["probability"],
        "ai_enabled":     bool(current_app.config.get("GROQ_API_KEY", "")),
        "active":         [r.to_dict() for r in active],
        "completed":      [r.to_dict() for r in completed],
    }


# ── Endpoints ──────────────────────────────────────────────────────────────

@ai_bp.get("/<user_id>/recommendations")
@require_auth()
def get_recommendations(user_id):
    """Return stored recommendations. Generates an initial set ONLY on the
    first-ever visit (when nothing is stored) — never on every page load."""
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403

    fl_risk = _fetch_fl_risk(user_id)

    if Recommendation.query.filter_by(user_id=user_id).count() == 0:
        for r in _generate_set(user_id, fl_risk):
            db.session.add(Recommendation(user_id=user_id, status="pending", **r))
        db.session.commit()

    return jsonify(_serialize(user_id, fl_risk))


@ai_bp.post("/<user_id>/recommendations/generate")
@require_auth()
def generate_recommendations(user_id):
    """Force a fresh set on demand. Archives current active ones, keeps history."""
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403

    fl_risk = _fetch_fl_risk(user_id)
    for r in _active_query(user_id).all():
        r.status = "refused"
    for r in _generate_set(user_id, fl_risk):
        db.session.add(Recommendation(user_id=user_id, status="pending", **r))
    db.session.commit()
    return jsonify(_serialize(user_id, fl_risk))


@ai_bp.post("/<user_id>/recommendations/<int:rid>/accept")
@require_auth()
def accept_recommendation(user_id, rid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    rec = Recommendation.query.filter_by(id=rid, user_id=user_id).first_or_404()
    rec.status = "accepted"
    db.session.commit()
    return jsonify(rec.to_dict())


@ai_bp.post("/<user_id>/recommendations/<int:rid>/complete")
@require_auth()
def complete_recommendation(user_id, rid):
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    rec = Recommendation.query.filter_by(id=rid, user_id=user_id).first_or_404()
    rec.status = "completed"
    db.session.commit()
    return jsonify(rec.to_dict())


@ai_bp.post("/<user_id>/recommendations/<int:rid>/refuse")
@require_auth()
def refuse_recommendation(user_id, rid):
    """Refuse a recommendation and return a replacement of the same category."""
    if not _can_access(user_id):
        return jsonify({"error": "Forbidden"}), 403
    rec = Recommendation.query.filter_by(id=rid, user_id=user_id).first_or_404()
    rec.status = "refused"

    avoid = [r.text for r in Recommendation.query.filter_by(
        user_id=user_id, category=rec.category).all()]
    fl_risk = _fetch_fl_risk(user_id)
    new = _generate_one(user_id, rec.category, avoid, fl_risk)
    replacement = Recommendation(user_id=user_id, status="pending", **new)
    db.session.add(replacement)
    db.session.commit()

    return jsonify({"refused": rid, "replacement": replacement.to_dict()})
