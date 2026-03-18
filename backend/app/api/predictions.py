from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.player import Player, PlayerMetrics
from app.models.prediction import Prediction
from app.ml.predictor import predict_injury_risk

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.post("/run/<int:player_id>")
@jwt_required()
def run_prediction(player_id):
    """Run injury risk prediction for a player using their latest metrics."""
    player = Player.query.get_or_404(player_id)
    latest = (
        PlayerMetrics.query.filter_by(player_id=player_id)
        .order_by(PlayerMetrics.recorded_at.desc())
        .first()
    )
    if not latest:
        return jsonify({"error": "No metrics recorded for this player"}), 400

    result = predict_injury_risk(player, latest)

    prediction = Prediction(
        player_id=player_id,
        injury_risk_score=result["injury_risk_score"],
        risk_level=result["risk_level"],
        model_version=result["model_version"],
        metrics_id=latest.id,
    )
    db.session.add(prediction)
    db.session.commit()
    return jsonify(prediction.to_dict()), 201


@predictions_bp.post("/run-team/<int:team_id>")
@jwt_required()
def run_team_predictions(team_id):
    """Run predictions for all active players in a team."""
    players = Player.query.filter_by(team_id=team_id, status="active").all()
    results = []
    for player in players:
        latest = (
            PlayerMetrics.query.filter_by(player_id=player.id)
            .order_by(PlayerMetrics.recorded_at.desc())
            .first()
        )
        if not latest:
            continue
        try:
            result = predict_injury_risk(player, latest)
            pred = Prediction(
                player_id=player.id,
                injury_risk_score=result["injury_risk_score"],
                risk_level=result["risk_level"],
                model_version=result["model_version"],
                metrics_id=latest.id,
            )
            db.session.add(pred)
            results.append({"player_id": player.id, **result})
        except Exception as e:
            results.append({"player_id": player.id, "error": str(e)})

    db.session.commit()
    return jsonify({"processed": len(results), "results": results})


@predictions_bp.get("/")
@jwt_required()
def list_predictions():
    player_id = request.args.get("player_id", type=int)
    team_id = request.args.get("team_id", type=int)
    risk_level = request.args.get("risk_level")
    limit = request.args.get("limit", 50, type=int)

    q = Prediction.query
    if player_id:
        q = q.filter_by(player_id=player_id)
    if team_id:
        player_ids = [p.id for p in Player.query.filter_by(team_id=team_id).all()]
        q = q.filter(Prediction.player_id.in_(player_ids))
    if risk_level:
        q = q.filter_by(risk_level=risk_level)

    preds = q.order_by(Prediction.predicted_at.desc()).limit(limit).all()
    return jsonify([p.to_dict() for p in preds])
