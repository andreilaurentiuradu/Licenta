from datetime import datetime, timezone
from app.extensions import db


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    predicted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    injury_risk_score = db.Column(db.Float, nullable=False)  # 0.0 - 1.0
    risk_level = db.Column(db.String(10), nullable=False)     # low | medium | high
    model_version = db.Column(db.Integer, nullable=False, default=0)
    metrics_id = db.Column(db.Integer, db.ForeignKey("player_metrics.id"), nullable=True)

    player = db.relationship("Player", back_populates="predictions")

    def to_dict(self):
        return {
            "id": self.id,
            "player_id": self.player_id,
            "predicted_at": self.predicted_at.isoformat(),
            "injury_risk_score": round(self.injury_risk_score, 4),
            "risk_level": self.risk_level,
            "model_version": self.model_version,
            "metrics_id": self.metrics_id,
        }
