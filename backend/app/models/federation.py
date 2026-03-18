from datetime import datetime, timezone
from app.extensions import db


class FLRound(db.Model):
    __tablename__ = "fl_rounds"

    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    # pending | active | aggregating | completed | failed
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    global_accuracy = db.Column(db.Float, nullable=True)
    global_loss = db.Column(db.Float, nullable=True)
    total_data_points = db.Column(db.Integer, default=0)
    model_version = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    updates = db.relationship("FLUpdate", back_populates="round")

    def to_dict(self):
        return {
            "id": self.id,
            "round_number": self.round_number,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "global_accuracy": round(self.global_accuracy, 4) if self.global_accuracy else None,
            "global_loss": round(self.global_loss, 4) if self.global_loss else None,
            "total_data_points": self.total_data_points,
            "model_version": self.model_version,
            "participating_teams": len(self.updates),
            "notes": self.notes,
        }


class FLUpdate(db.Model):
    __tablename__ = "fl_updates"

    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("fl_rounds.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    local_data_points = db.Column(db.Integer, nullable=False)
    local_accuracy = db.Column(db.Float, nullable=True)
    local_loss = db.Column(db.Float, nullable=True)
    # model_params stored as JSON text (W1, b1, W2, b2 serialized)
    model_params_json = db.Column(db.Text, nullable=False)

    round = db.relationship("FLRound", back_populates="updates")
    team = db.relationship("Team", back_populates="fl_updates")

    def to_dict(self):
        return {
            "id": self.id,
            "round_id": self.round_id,
            "team_id": self.team_id,
            "team_name": self.team.name if self.team else None,
            "submitted_at": self.submitted_at.isoformat(),
            "local_data_points": self.local_data_points,
            "local_accuracy": round(self.local_accuracy, 4) if self.local_accuracy else None,
            "local_loss": round(self.local_loss, 4) if self.local_loss else None,
        }
