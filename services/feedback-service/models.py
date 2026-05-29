from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Feedback(db.Model):
    __tablename__ = "feedback"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.String(36),  nullable=False)
    username   = db.Column(db.String(64),  nullable=False)
    ratings    = db.Column(db.JSON,        nullable=False)
    message    = db.Column(db.Text,        nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "username":   self.username,
            "ratings":    self.ratings,
            "message":    self.message,
            "created_at": self.created_at.isoformat(),
        }
