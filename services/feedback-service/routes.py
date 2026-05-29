from flask import Blueprint, request, jsonify, g
from models import db, Feedback
from auth import require_auth

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.post("/")
@require_auth()
def submit_feedback():
    data    = request.get_json(silent=True) or {}
    ratings = data.get("ratings")
    message = data.get("message", "")

    if not ratings or not isinstance(ratings, dict):
        return jsonify({"error": "ratings must be a non-empty object"}), 400

    claims = g.claims
    fb = Feedback(
        user_id  = claims["sub"],
        username = claims.get("preferred_username", ""),
        ratings  = ratings,
        message  = message,
    )
    db.session.add(fb)
    db.session.commit()

    return jsonify({"message": "Feedback saved", "id": fb.id}), 201


@feedback_bp.get("/")
@require_auth(roles=["admin"])
def list_feedback():
    items = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return jsonify([f.to_dict() for f in items])
