"""
Feature extraction: maps live DB data → 12-feature numpy vectors
matching the Kaggle notebook's FEATURES list used for FL training.

Feature mapping:
  Position                → PlayerProfile.position          (label-encoded)
  Previous_Injury_Count   → COUNT(InjuryRecord)
  Knee_Strength_Score     → PhysicalAssessment (latest)
  Hamstring_Flexibility   → PhysicalAssessment (latest)
  Reaction_Time_ms        → PhysicalAssessment (latest)
  Balance_Test_Score      → PhysicalAssessment (latest)
  Sprint_Speed_10m_s      → PhysicalAssessment (latest)
  Agility_Score           → PhysicalAssessment (latest)
  Sleep_Hours_Per_Night   → AVG(WellnessLog.sleep_hours,  last 90d)
  Stress_Level_Score      → AVG(WellnessLog.stress_level, last 90d)
  Nutrition_Quality_Score → AVG(WellnessLog.nutrition_score, last 90d)
  Warmup_Routine_Adherence→ AVG(TrainingLog.warmup_adherence, last 90d)

Missing values are filled with dataset means so every player with
at least a profile row can contribute a feature vector.
"""

import json
import logging
from datetime import date, timedelta

import numpy as np
from sqlalchemy import func

from fl.model import FEATURES, POSITION_CLASSES

log = logging.getLogger(__name__)

# Dataset means from the Kaggle notebook — used as fallback for NULL fields
_MEANS = {
    "Position":                  1,      # Forward
    "Previous_Injury_Count":     1.54,
    "Knee_Strength_Score":       74.93,
    "Hamstring_Flexibility":     79.15,
    "Reaction_Time_ms":          249.42,
    "Balance_Test_Score":        83.83,
    "Sprint_Speed_10m_s":        5.95,
    "Agility_Score":             78.34,
    "Sleep_Hours_Per_Night":     7.42,
    "Stress_Level_Score":        54.04,
    "Nutrition_Quality_Score":   74.38,
    "Warmup_Routine_Adherence":  0.60,
}

_POSITION_MAP = {p: i for i, p in enumerate(POSITION_CLASSES)}


def _val(v, key: str) -> float:
    return float(v) if v is not None else float(_MEANS[key])


def compute_nutrition_score(calories, protein_g, carbs_g, fat_g, hydration_ml) -> float:
    """
    Derive a 0-100 Nutrition_Quality_Score from raw macro data.
    Based on sports nutrition guidelines for football players.
    """
    score = 50.0
    if calories:
        if 2500 <= calories <= 3500:
            score += 15
        elif 2000 <= calories < 2500 or 3500 < calories <= 4000:
            score += 7
    if protein_g and protein_g >= 120:
        score += 15 if protein_g >= 150 else 8
    if hydration_ml:
        if hydration_ml >= 2500:
            score += 10
        elif hydration_ml >= 2000:
            score += 5
    if carbs_g and fat_g and protein_g:
        total_cals = protein_g * 4 + carbs_g * 4 + fat_g * 9
        if total_cals > 0:
            carb_pct = carbs_g * 4 / total_cals * 100
            if 45 <= carb_pct <= 65:
                score += 10
    return round(min(100.0, max(0.0, score)), 2)


def player_feature_vector(user_id: str) -> np.ndarray | None:
    """
    Build the 12-feature vector for one player from DB data.
    Returns None only if the PlayerProfile row does not exist at all.
    Missing sub-fields are filled with dataset means.
    """
    from app.models import (
        PlayerProfile, PhysicalAssessment, InjuryRecord,
        WellnessLog, TrainingLog,
    )
    from app.extensions import db

    prof = PlayerProfile.query.filter_by(user_id=user_id).first()
    if not prof:
        return None

    last_90 = date.today() - timedelta(days=90)

    phys = (PhysicalAssessment.query
            .filter_by(user_id=user_id)
            .order_by(PhysicalAssessment.date.desc())
            .first())

    w = db.session.query(
        func.avg(WellnessLog.sleep_hours).label("sleep"),
        func.avg(WellnessLog.stress_level).label("stress"),
        func.avg(WellnessLog.nutrition_score).label("nutrition"),
    ).filter(
        WellnessLog.user_id == user_id,
        WellnessLog.date >= last_90,
    ).first()

    t = db.session.query(
        func.avg(TrainingLog.warmup_adherence).label("warmup"),
    ).filter(
        TrainingLog.user_id == user_id,
        TrainingLog.date >= last_90,
    ).first()

    inj_count = InjuryRecord.query.filter_by(user_id=user_id).count()

    pos = float(_POSITION_MAP.get(prof.position or "", _MEANS["Position"]))

    vec = np.array([
        pos,
        float(inj_count),
        _val(phys.knee_strength_score   if phys else None, "Knee_Strength_Score"),
        _val(phys.hamstring_flexibility if phys else None, "Hamstring_Flexibility"),
        _val(phys.reaction_time_ms      if phys else None, "Reaction_Time_ms"),
        _val(phys.balance_test_score    if phys else None, "Balance_Test_Score"),
        _val(phys.sprint_speed_10m_s    if phys else None, "Sprint_Speed_10m_s"),
        _val(phys.agility_score         if phys else None, "Agility_Score"),
        _val(w.sleep     if w else None, "Sleep_Hours_Per_Night"),
        _val(w.stress    if w else None, "Stress_Level_Score"),
        _val(w.nutrition if w else None, "Nutrition_Quality_Score"),
        _val(t.warmup    if t else None, "Warmup_Routine_Adherence"),
    ], dtype=float)

    return vec


def extract_club_dataset(club: str):
    """
    Build (X, y) arrays for all players in a club.

    y = 1 if player has ≥1 injury record (proxy for historical injury risk), else 0.

    Returns (None, None) if fewer than 2 players have vectors,
    or if only one class is present (can't train binary classifier).
    """
    from app.models import PlayerProfile, InjuryRecord

    profiles = PlayerProfile.query.filter_by(club=club).all()
    X_rows, y_rows = [], []

    for p in profiles:
        vec = player_feature_vector(p.user_id)
        if vec is None:
            continue
        label = 1 if InjuryRecord.query.filter_by(user_id=p.user_id).count() > 0 else 0
        X_rows.append(vec)
        y_rows.append(label)

    if len(X_rows) < 2:
        log.debug("[FL features] Club %r: only %d player(s) — need ≥2.", club, len(X_rows))
        return None, None

    X = np.array(X_rows)
    y = np.array(y_rows)

    if len(np.unique(y)) < 2:
        log.debug("[FL features] Club %r: only one class in y — skipping.", club)
        return None, None

    return X, y


def predict_injury_risk(user_id: str) -> dict:
    """
    Run the current global FL model on one player.
    Returns {"risk": "low"|"medium"|"high", "probability": float}.
    Falls back to {"risk": "low", "probability": 0.0} if model or data absent.
    """
    from app.models import FLGlobalModel

    vec = player_feature_vector(user_id)
    if vec is None:
        return {"risk": "low", "probability": 0.0}

    global_m = FLGlobalModel.query.order_by(FLGlobalModel.id.desc()).first()
    if not global_m:
        return {"risk": "low", "probability": 0.0}

    from fl.model import build_model, set_params

    coef      = np.array(json.loads(global_m.coef_json))
    intercept = np.array(json.loads(global_m.intercept_json))
    model     = build_model()
    set_params(model, coef, intercept)

    prob = float(model.predict_proba(vec.reshape(1, -1))[0][1])
    risk = "high" if prob >= 0.65 else "medium" if prob >= 0.40 else "low"
    return {"risk": risk, "probability": round(prob, 4)}
