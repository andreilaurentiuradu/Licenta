from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from app.extensions import db
from app.models.player import Player
from app.models.prediction import Prediction
from app.models.federation import FLRound
from app.models.team import Team

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/overview")
@jwt_required()
def overview():
    team_id = request.args.get("team_id", type=int)

    player_q = Player.query
    pred_q = Prediction.query
    if team_id:
        player_q = player_q.filter_by(team_id=team_id)
        player_ids = [p.id for p in player_q.all()]
        pred_q = pred_q.filter(Prediction.player_id.in_(player_ids))

    total_players = player_q.count()
    injured = player_q.filter_by(status="injured").count()
    recovery = player_q.filter_by(status="recovery").count()
    active = player_q.filter_by(status="active").count()
    total_predictions = pred_q.count()

    high_risk = pred_q.filter_by(risk_level="high").count()
    medium_risk = pred_q.filter_by(risk_level="medium").count()
    low_risk = pred_q.filter_by(risk_level="low").count()

    fl_rounds = FLRound.query.filter_by(status="completed").count()
    last_round = FLRound.query.filter_by(status="completed").order_by(FLRound.round_number.desc()).first()

    return jsonify({
        "players": {
            "total": total_players,
            "active": active,
            "injured": injured,
            "recovery": recovery,
        },
        "predictions": {
            "total": total_predictions,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
        },
        "federation": {
            "completed_rounds": fl_rounds,
            "latest_accuracy": round(last_round.global_accuracy, 4) if last_round and last_round.global_accuracy else None,
            "model_version": last_round.model_version if last_round else 0,
        },
    })


@analytics_bp.get("/risk-distribution")
@jwt_required()
def risk_distribution():
    team_id = request.args.get("team_id", type=int)

    q = db.session.query(
        Player.position,
        Prediction.risk_level,
        func.count(Prediction.id).label("count"),
    ).join(Prediction, Player.id == Prediction.player_id)

    if team_id:
        q = q.filter(Player.team_id == team_id)

    rows = q.group_by(Player.position, Prediction.risk_level).all()
    result = {}
    for pos, level, count in rows:
        if pos not in result:
            result[pos] = {"low": 0, "medium": 0, "high": 0}
        result[pos][level] = count

    return jsonify(result)


@analytics_bp.get("/fl-history")
@jwt_required()
def fl_history():
    rounds = (
        FLRound.query.filter_by(status="completed")
        .order_by(FLRound.round_number.asc())
        .all()
    )
    return jsonify([
        {
            "round": r.round_number,
            "accuracy": round(r.global_accuracy, 4) if r.global_accuracy else None,
            "loss": round(r.global_loss, 4) if r.global_loss else None,
            "data_points": r.total_data_points,
            "date": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rounds
    ])


@analytics_bp.get("/team-comparison")
@jwt_required()
def team_comparison():
    teams = Team.query.all()
    result = []
    for team in teams:
        player_ids = [p.id for p in team.players]
        if not player_ids:
            continue
        high = Prediction.query.filter(
            Prediction.player_id.in_(player_ids), Prediction.risk_level == "high"
        ).count()
        medium = Prediction.query.filter(
            Prediction.player_id.in_(player_ids), Prediction.risk_level == "medium"
        ).count()
        low = Prediction.query.filter(
            Prediction.player_id.in_(player_ids), Prediction.risk_level == "low"
        ).count()
        result.append({
            "team": team.name,
            "high": high,
            "medium": medium,
            "low": low,
            "total_players": len(team.players),
        })
    return jsonify(result)
