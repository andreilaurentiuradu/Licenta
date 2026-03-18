from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.team import Team

teams_bp = Blueprint("teams", __name__)


@teams_bp.get("/")
@jwt_required()
def list_teams():
    teams = Team.query.all()
    return jsonify([t.to_dict() for t in teams])


@teams_bp.post("/")
@jwt_required()
def create_team():
    data = request.get_json()
    team = Team(
        name=data["name"],
        city=data.get("city", ""),
        sport=data.get("sport", "Football"),
        fl_participant=data.get("fl_participant", True),
    )
    db.session.add(team)
    db.session.commit()
    return jsonify(team.to_dict()), 201


@teams_bp.get("/<int:team_id>")
@jwt_required()
def get_team(team_id):
    team = Team.query.get_or_404(team_id)
    return jsonify(team.to_dict())
