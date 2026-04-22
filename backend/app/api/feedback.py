from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Feedback
from app.api.keycloak_auth import keycloak_required

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.post("/")
@keycloak_required()
def submit_feedback():
    data    = request.get_json(silent=True) or {}
    ratings = data.get("ratings")
    message = data.get("message", "")

    if not ratings or not isinstance(ratings, dict):
        return jsonify({"error": "ratings must be a non-empty object"}), 400

    claims = request.kc_claims
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
@keycloak_required(roles=["admin"])
def list_feedback():
    items = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return jsonify([f.to_dict() for f in items])
