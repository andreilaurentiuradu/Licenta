from datetime import datetime, timezone
from app.extensions import db


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(20), nullable=False)  # Defender/Forward/Goalkeeper/Midfielder
    age = db.Column(db.Integer, nullable=False)
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    nationality = db.Column(db.String(60), default="Romanian")
    status = db.Column(db.String(20), default="active")  # active | injured | recovery
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    team = db.relationship("Team", back_populates="players")
    metrics = db.relationship("PlayerMetrics", back_populates="player", order_by="PlayerMetrics.recorded_at.desc()")
    predictions = db.relationship("Prediction", back_populates="player", order_by="Prediction.predicted_at.desc()")

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            return round(self.weight_kg / ((self.height_cm / 100) ** 2), 2)
        return None

    @property
    def latest_prediction(self):
        return self.predictions[0] if self.predictions else None

    def to_dict(self, include_metrics=False):
        d = {
            "id": self.id,
            "full_name": self.full_name,
            "position": self.position,
            "age": self.age,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "bmi": self.bmi,
            "nationality": self.nationality,
            "status": self.status,
            "team_id": self.team_id,
            "team_name": self.team.name if self.team else None,
            "joined_at": self.joined_at.isoformat(),
            "latest_risk": self.latest_prediction.to_dict() if self.latest_prediction else None,
        }
        if include_metrics:
            d["metrics_history"] = [m.to_dict() for m in self.metrics[:10]]
        return d


class PlayerMetrics(db.Model):
    __tablename__ = "player_metrics"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    training_hours_per_week = db.Column(db.Float, nullable=False)
    matches_played_past_season = db.Column(db.Integer, nullable=False)
    previous_injury_count = db.Column(db.Integer, nullable=False, default=0)
    knee_strength_score = db.Column(db.Float, nullable=False)
    hamstring_flexibility = db.Column(db.Float, nullable=False)
    reaction_time_ms = db.Column(db.Float, nullable=False)
    balance_test_score = db.Column(db.Float, nullable=False)
    sprint_speed_10m_s = db.Column(db.Float, nullable=False)
    agility_score = db.Column(db.Float, nullable=False)
    sleep_hours_per_night = db.Column(db.Float, nullable=False)
    stress_level_score = db.Column(db.Float, nullable=False)
    nutrition_quality_score = db.Column(db.Float, nullable=False)
    warmup_routine_adherence = db.Column(db.Float, nullable=False)

    player = db.relationship("Player", back_populates="metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "player_id": self.player_id,
            "recorded_at": self.recorded_at.isoformat(),
            "training_hours_per_week": self.training_hours_per_week,
            "matches_played_past_season": self.matches_played_past_season,
            "previous_injury_count": self.previous_injury_count,
            "knee_strength_score": self.knee_strength_score,
            "hamstring_flexibility": self.hamstring_flexibility,
            "reaction_time_ms": self.reaction_time_ms,
            "balance_test_score": self.balance_test_score,
            "sprint_speed_10m_s": self.sprint_speed_10m_s,
            "agility_score": self.agility_score,
            "sleep_hours_per_night": self.sleep_hours_per_night,
            "stress_level_score": self.stress_level_score,
            "nutrition_quality_score": self.nutrition_quality_score,
            "warmup_routine_adherence": self.warmup_routine_adherence,
        }
