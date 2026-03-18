"""
Federated Learning API.

Simulates a centralized FL workflow:
  1. POST /start   — create a new round, train all teams locally, aggregate
  2. GET  /rounds  — list all rounds
  3. GET  /status  — current global model info
  4. GET  /rounds/<id> — round details
"""

import json
import numpy as np
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.team import Team
from app.models.player import Player, PlayerMetrics
from app.models.federation import FLRound, FLUpdate
from app.ml.model import NeuralNetwork, POSITION_CLASSES, NUMERICAL_FEATURES
from app.ml.federated import federated_average, simulate_local_training
from app.ml.predictor import load_global_model, save_global_model, load_scaler

federation_bp = Blueprint("federation", __name__)


def _build_team_dataset(team_id: int, scaler: dict):
    """Build (X, y) for a team from PlayerMetrics + Player data."""
    players = Player.query.filter_by(team_id=team_id).all()
    X_rows, y_rows = [], []

    mean = np.array(scaler["mean"])
    std = np.array(scaler["std"])
    std = np.where(std == 0, 1.0, std)

    for player in players:
        metrics_list = (
            PlayerMetrics.query.filter_by(player_id=player.id)
            .order_by(PlayerMetrics.recorded_at.desc())
            .all()
        )
        for m in metrics_list:
            nums = [
                player.age, player.height_cm, player.weight_kg,
                player.bmi or 0,
                m.training_hours_per_week, m.matches_played_past_season,
                m.previous_injury_count, m.knee_strength_score,
                m.hamstring_flexibility, m.reaction_time_ms,
                m.balance_test_score, m.sprint_speed_10m_s,
                m.agility_score, m.sleep_hours_per_night,
                m.stress_level_score, m.nutrition_quality_score,
                m.warmup_routine_adherence,
            ]
            nums = (np.array(nums, dtype=float) - mean) / std
            pos = [1.0 if cls == player.position else 0.0 for cls in POSITION_CLASSES]
            X_rows.append(np.concatenate([nums, pos]))

            # Use latest prediction as label, else default 0
            pred = player.predictions[0] if player.predictions else None
            y_rows.append(1 if (pred and pred.risk_level == "high") else 0)

    if not X_rows:
        return None, None

    return np.array(X_rows), np.array(y_rows, dtype=float)


@federation_bp.post("/start")
@jwt_required()
def start_round():
    """
    Trigger a full FL round:
    1. Each participating team trains locally (simulated)
    2. FedAvg aggregates parameters
    3. Global model is updated and persisted
    """
    scaler = load_scaler()
    if scaler is None:
        return jsonify({"error": "System not initialised. Run /api/federation/init first."}), 400

    teams = Team.query.filter_by(fl_participant=True).all()
    if len(teams) < 2:
        return jsonify({"error": "At least 2 FL-participant teams required."}), 400

    # Determine round number
    last = FLRound.query.order_by(FLRound.round_number.desc()).first()
    round_number = (last.round_number + 1) if last else 1
    new_version = (last.model_version + 1) if last else 1

    fl_round = FLRound(
        round_number=round_number,
        status="active",
        model_version=new_version,
    )
    db.session.add(fl_round)
    db.session.flush()

    global_model = load_global_model()
    client_params, client_sizes, updates = [], [], []

    epochs = current_app.config["FL_LOCAL_EPOCHS"]
    lr = current_app.config["FL_LEARNING_RATE"]

    for team in teams:
        X, y = _build_team_dataset(team.id, scaler)
        if X is None or len(X) == 0:
            continue

        updated_params, stats = simulate_local_training(global_model, X, y, epochs=epochs, lr=lr)

        update = FLUpdate(
            round_id=fl_round.id,
            team_id=team.id,
            local_data_points=len(X),
            local_accuracy=stats["accuracy"],
            local_loss=stats["loss"],
            model_params_json=json.dumps(updated_params),
        )
        db.session.add(update)
        client_params.append(updated_params)
        client_sizes.append(len(X))
        updates.append(stats)

    if len(client_params) < 2:
        fl_round.status = "failed"
        fl_round.notes = "Insufficient client data."
        db.session.commit()
        return jsonify({"error": "Not enough client data for aggregation."}), 400

    # FedAvg aggregation
    aggregated = federated_average(client_params, client_sizes)
    global_model.set_params(aggregated)
    save_global_model(global_model)

    # Evaluate aggregated model on all data combined
    all_X = np.vstack([_build_team_dataset(t.id, scaler)[0] for t in teams
                       if _build_team_dataset(t.id, scaler)[0] is not None])
    all_y = np.hstack([_build_team_dataset(t.id, scaler)[1] for t in teams
                       if _build_team_dataset(t.id, scaler)[1] is not None])

    preds = global_model.predict(all_X)
    global_acc = float(np.mean(preds == all_y))
    y_prob = global_model.predict_proba(all_X)
    eps = 1e-8
    global_loss = float(-np.mean(all_y * np.log(y_prob + eps) + (1 - all_y) * np.log(1 - y_prob + eps)))

    fl_round.status = "completed"
    fl_round.completed_at = datetime.now(timezone.utc)
    fl_round.global_accuracy = global_acc
    fl_round.global_loss = global_loss
    fl_round.total_data_points = sum(client_sizes)
    db.session.commit()

    return jsonify({
        "round": fl_round.to_dict(),
        "client_count": len(client_params),
        "aggregation": "FedAvg",
    }), 201


@federation_bp.get("/rounds")
@jwt_required()
def list_rounds():
    rounds = FLRound.query.order_by(FLRound.round_number.desc()).all()
    return jsonify([r.to_dict() for r in rounds])


@federation_bp.get("/rounds/<int:round_id>")
@jwt_required()
def get_round(round_id):
    fl_round = FLRound.query.get_or_404(round_id)
    data = fl_round.to_dict()
    data["updates"] = [u.to_dict() for u in fl_round.updates]
    return jsonify(data)


@federation_bp.get("/status")
@jwt_required()
def status():
    last = FLRound.query.filter_by(status="completed").order_by(FLRound.round_number.desc()).first()
    teams = Team.query.filter_by(fl_participant=True).all()
    return jsonify({
        "total_rounds": FLRound.query.count(),
        "current_model_version": last.model_version if last else 0,
        "last_global_accuracy": round(last.global_accuracy, 4) if last and last.global_accuracy else None,
        "participating_teams": len(teams),
        "teams": [{"id": t.id, "name": t.name, "data_points": t.local_data_points} for t in teams],
    })


@federation_bp.post("/init")
@jwt_required()
def init_federation():
    """Re-initialise the global model with random weights (for demos/resets)."""
    model = NeuralNetwork()
    save_global_model(model)
    return jsonify({"message": "Global model reinitialised.", "model_version": 0})
