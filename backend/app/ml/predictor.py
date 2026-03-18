"""
Inference engine: loads global model + scaler, returns injury risk.
"""

import os
import json
import numpy as np
from flask import current_app
from app.ml.model import NeuralNetwork, NUMERICAL_FEATURES, POSITION_CLASSES


def _model_path(app=None) -> str:
    base = (app or current_app).config["MODEL_DIR"]
    return os.path.join(base, "global_model.json")


def _scaler_path(app=None) -> str:
    base = (app or current_app).config["MODEL_DIR"]
    return os.path.join(base, "scaler.json")


def load_global_model() -> NeuralNetwork:
    path = _model_path()
    model = NeuralNetwork()
    if os.path.exists(path):
        model.load(path)
    return model


def save_global_model(model: NeuralNetwork):
    model.save(_model_path())


def load_scaler() -> dict:
    path = _scaler_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def save_scaler(scaler: dict):
    with open(_scaler_path(), "w") as f:
        json.dump(scaler, f)


def preprocess(metrics_dict: dict, player_position: str, scaler: dict) -> np.ndarray:
    """
    Build the 21-feature input vector from player metrics.

    Args:
        metrics_dict:    dict with keys matching NUMERICAL_FEATURES
        player_position: e.g. "Midfielder"
        scaler:          {'mean': [...], 'std': [...]} for numerical features

    Returns:
        Normalised feature vector, shape (1, 21)
    """
    # Map model feature names to metrics dict keys
    key_map = {
        "Training_Hours_Per_Week": "training_hours_per_week",
        "Matches_Played_Past_Season": "matches_played_past_season",
        "Previous_Injury_Count": "previous_injury_count",
        "Knee_Strength_Score": "knee_strength_score",
        "Hamstring_Flexibility": "hamstring_flexibility",
        "Reaction_Time_ms": "reaction_time_ms",
        "Balance_Test_Score": "balance_test_score",
        "Sprint_Speed_10m_s": "sprint_speed_10m_s",
        "Agility_Score": "agility_score",
        "Sleep_Hours_Per_Night": "sleep_hours_per_night",
        "Stress_Level_Score": "stress_level_score",
        "Nutrition_Quality_Score": "nutrition_quality_score",
        "Warmup_Routine_Adherence": "warmup_routine_adherence",
    }

    nums = []
    for feat in NUMERICAL_FEATURES:
        if feat in ("Age", "Height_cm", "Weight_kg", "BMI"):
            nums.append(metrics_dict.get(feat, 0.0))
        else:
            nums.append(metrics_dict.get(key_map.get(feat, feat), 0.0))

    nums = np.array(nums, dtype=float)

    # Standardise
    mean = np.array(scaler["mean"])
    std = np.array(scaler["std"])
    std = np.where(std == 0, 1.0, std)
    nums = (nums - mean) / std

    # One-hot encode position
    pos_vec = np.array([1.0 if cls == player_position else 0.0 for cls in POSITION_CLASSES])

    feature_vec = np.concatenate([nums, pos_vec]).reshape(1, -1)
    return feature_vec


def predict_injury_risk(player, latest_metrics) -> dict:
    """
    Run inference for a player given their latest metrics.

    Returns:
        {injury_risk_score: float, risk_level: str, model_version: int}
    """
    scaler = load_scaler()
    if scaler is None:
        raise RuntimeError("Scaler not initialised. Run the seeder first.")

    metrics = {
        "Age": float(player.age),
        "Height_cm": float(player.height_cm),
        "Weight_kg": float(player.weight_kg),
        "BMI": float(player.bmi or 0),
    }
    metrics.update(latest_metrics.to_dict())

    X = preprocess(metrics, player.position, scaler)
    model = load_global_model()
    score = float(model.predict_proba(X)[0])

    if score < 0.35:
        level = "low"
    elif score < 0.65:
        level = "medium"
    else:
        level = "high"

    # Determine current model version from rounds
    version = _current_model_version()

    return {"injury_risk_score": score, "risk_level": level, "model_version": version}


def _current_model_version() -> int:
    """Return the model version from the latest completed FL round."""
    try:
        from app.models.federation import FLRound
        latest = FLRound.query.filter_by(status="completed").order_by(
            FLRound.model_version.desc()
        ).first()
        return latest.model_version if latest else 0
    except Exception:
        return 0
