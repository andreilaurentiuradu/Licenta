from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.player import Player, PlayerMetrics

players_bp = Blueprint("players", __name__)


@players_bp.get("/")
@jwt_required()
def list_players():
    team_id = request.args.get("team_id", type=int)
    position = request.args.get("position")
    status = request.args.get("status")
    q = Player.query
    if team_id:
        q = q.filter_by(team_id=team_id)
    if position:
        q = q.filter_by(position=position)
    if status:
        q = q.filter_by(status=status)
    players = q.order_by(Player.full_name).all()
    return jsonify([p.to_dict() for p in players])


@players_bp.post("/")
@jwt_required()
def create_player():
    data = request.get_json()
    player = Player(
        full_name=data["full_name"],
        position=data["position"],
        age=data["age"],
        height_cm=data["height_cm"],
        weight_kg=data["weight_kg"],
        nationality=data.get("nationality", "Romanian"),
        status=data.get("status", "active"),
        team_id=data["team_id"],
    )
    db.session.add(player)
    db.session.commit()
    return jsonify(player.to_dict()), 201


@players_bp.get("/<int:player_id>")
@jwt_required()
def get_player(player_id):
    player = Player.query.get_or_404(player_id)
    return jsonify(player.to_dict(include_metrics=True))


@players_bp.put("/<int:player_id>")
@jwt_required()
def update_player(player_id):
    player = Player.query.get_or_404(player_id)
    data = request.get_json()
    for field in ("full_name", "position", "age", "height_cm", "weight_kg", "nationality", "status"):
        if field in data:
            setattr(player, field, data[field])
    db.session.commit()
    return jsonify(player.to_dict())


@players_bp.delete("/<int:player_id>")
@jwt_required()
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    db.session.delete(player)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@players_bp.post("/<int:player_id>/metrics")
@jwt_required()
def add_metrics(player_id):
    player = Player.query.get_or_404(player_id)
    data = request.get_json()
    metrics = PlayerMetrics(
        player_id=player.id,
        training_hours_per_week=data["training_hours_per_week"],
        matches_played_past_season=data["matches_played_past_season"],
        previous_injury_count=data.get("previous_injury_count", 0),
        knee_strength_score=data["knee_strength_score"],
        hamstring_flexibility=data["hamstring_flexibility"],
        reaction_time_ms=data["reaction_time_ms"],
        balance_test_score=data["balance_test_score"],
        sprint_speed_10m_s=data["sprint_speed_10m_s"],
        agility_score=data["agility_score"],
        sleep_hours_per_night=data["sleep_hours_per_night"],
        stress_level_score=data["stress_level_score"],
        nutrition_quality_score=data["nutrition_quality_score"],
        warmup_routine_adherence=data["warmup_routine_adherence"],
    )
    db.session.add(metrics)
    db.session.commit()
    return jsonify(metrics.to_dict()), 201


@players_bp.get("/<int:player_id>/metrics")
@jwt_required()
def get_metrics(player_id):
    Player.query.get_or_404(player_id)
    metrics = (
        PlayerMetrics.query.filter_by(player_id=player_id)
        .order_by(PlayerMetrics.recorded_at.desc())
        .limit(20)
        .all()
    )
    return jsonify([m.to_dict() for m in metrics])
