from datetime import datetime, timezone
from app.extensions import db


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    sport = db.Column(db.String(50), nullable=False, default="Football")
    fl_participant = db.Column(db.Boolean, default=True)
    local_data_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    users = db.relationship("User", back_populates="team")
    players = db.relationship("Player", back_populates="team")
    fl_updates = db.relationship("FLUpdate", back_populates="team")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "sport": self.sport,
            "fl_participant": self.fl_participant,
            "local_data_points": self.local_data_points,
            "player_count": len(self.players),
            "created_at": self.created_at.isoformat(),
        }
