"""
Shared model definition for the injury-prediction FL pipeline.

Features selected from the Kaggle correlation analysis (dropped: Age,
Height_cm, Weight_kg, BMI, Training_Hours_Per_Week, Matches_Played_Past_Season).

Mapping to platform DB (app/models.py):
    Position              → PlayerProfile.position
    Previous_Injury_Count → COUNT(InjuryRecord) per player
    Knee_Strength_Score   → PhysicalAssessment.knee_strength_score  (latest)
    Hamstring_Flexibility → PhysicalAssessment.hamstring_flexibility (latest)
    Reaction_Time_ms      → PhysicalAssessment.reaction_time_ms      (latest)
    Balance_Test_Score    → PhysicalAssessment.balance_test_score     (latest) *
    Sprint_Speed_10m_s    → PhysicalAssessment.sprint_speed_10m_s    (latest) *
    Agility_Score         → PhysicalAssessment.agility_score          (latest) *
    Sleep_Hours_Per_Night → AVG(WellnessLog.sleep_hours)
    Stress_Level_Score    → AVG(WellnessLog.stress_level)
    Nutrition_Quality_Score → derived from WellnessLog macros         *
    Warmup_Routine_Adherence → TrainingLog.warmup_adherence           *

  (*) fields to be added to DB models in Sprint 3
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

FEATURES = [
    'Position',
    'Previous_Injury_Count',
    'Knee_Strength_Score',
    'Hamstring_Flexibility',
    'Reaction_Time_ms',
    'Balance_Test_Score',
    'Sprint_Speed_10m_s',
    'Agility_Score',
    'Sleep_Hours_Per_Night',
    'Stress_Level_Score',
    'Nutrition_Quality_Score',
    'Warmup_Routine_Adherence',
]
TARGET   = 'Injury_Next_Season'
N_FEATURES = len(FEATURES)

POSITION_CLASSES = ['Defender', 'Forward', 'Goalkeeper', 'Midfielder']


def build_model() -> LogisticRegression:
    """Return a fresh Logistic Regression ready for FL warm-start training."""
    return LogisticRegression(max_iter=1000, random_state=42, warm_start=True)


def get_params(model: LogisticRegression):
    """Extract model parameters as plain numpy arrays (coef, intercept)."""
    return model.coef_.copy(), model.intercept_.copy()


def set_params(model: LogisticRegression, coef: np.ndarray, intercept: np.ndarray):
    """Inject global parameters before local training."""
    model.coef_      = coef.copy()
    model.intercept_ = intercept.copy()
    model.classes_   = np.array([0, 1])
    return model


def encode_position(series):
    le = LabelEncoder()
    le.classes_ = np.array(POSITION_CLASSES)
    return le.transform(series)


def preprocess(df):
    """Apply the same preprocessing as the Kaggle notebook."""
    import pandas as pd
    df = df.drop(columns=[
        'Age', 'Matches_Played_Past_Season', 'Training_Hours_Per_Week',
        'BMI', 'Height_cm', 'Weight_kg',
    ], errors='ignore')
    df = df.copy()
    df['Position'] = encode_position(df['Position'])
    return df
