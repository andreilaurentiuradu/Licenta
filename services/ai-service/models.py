from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class PlayerProfile(db.Model):
    __tablename__ = "player_profiles"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.String(36), unique=True, nullable=False)
    username   = db.Column(db.String(64), nullable=False)
    club       = db.Column(db.String(64))
    position   = db.Column(db.String(32))
    height_cm  = db.Column(db.Float)
    weight_kg  = db.Column(db.Float)
    birth_year = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "username":   self.username,
            "club":       self.club,
            "position":   self.position,
            "height_cm":  self.height_cm,
            "weight_kg":  self.weight_kg,
            "birth_year": self.birth_year,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TrainingLog(db.Model):
    __tablename__ = "training_logs"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.String(36), nullable=False, index=True)
    date             = db.Column(db.Date, nullable=False)
    training_hours   = db.Column(db.Float)
    matches_played   = db.Column(db.Integer, default=0)
    warmup_adherence = db.Column(db.Float)
    notes            = db.Column(db.Text)

    def to_dict(self):
        return {
            "id":               self.id,
            "user_id":          self.user_id,
            "date":             self.date.isoformat(),
            "training_hours":   self.training_hours,
            "matches_played":   self.matches_played,
            "warmup_adherence": self.warmup_adherence,
            "notes":            self.notes,
        }


class PhysicalAssessment(db.Model):
    __tablename__ = "physical_assessments"

    id                    = db.Column(db.Integer, primary_key=True)
    user_id               = db.Column(db.String(36), nullable=False, index=True)
    date                  = db.Column(db.Date, nullable=False)
    knee_strength_score   = db.Column(db.Float)
    hamstring_flexibility = db.Column(db.Float)
    reaction_time_ms      = db.Column(db.Float)
    balance_test_score    = db.Column(db.Float)
    sprint_speed_10m_s    = db.Column(db.Float)
    agility_score         = db.Column(db.Float)

    def to_dict(self):
        return {
            "id":                    self.id,
            "user_id":               self.user_id,
            "date":                  self.date.isoformat(),
            "knee_strength_score":   self.knee_strength_score,
            "hamstring_flexibility": self.hamstring_flexibility,
            "reaction_time_ms":      self.reaction_time_ms,
            "balance_test_score":    self.balance_test_score,
            "sprint_speed_10m_s":    self.sprint_speed_10m_s,
            "agility_score":         self.agility_score,
        }


class InjuryRecord(db.Model):
    __tablename__ = "injury_records"

    id                     = db.Column(db.Integer, primary_key=True)
    user_id                = db.Column(db.String(36), nullable=False, index=True)
    date                   = db.Column(db.Date, nullable=False)
    injury_type            = db.Column(db.String(64))
    injury_severity        = db.Column(db.String(16))
    rehabilitation_program = db.Column(db.String(128))
    rehabilitation_weeks   = db.Column(db.Integer)
    recurrence             = db.Column(db.Boolean, default=False)
    notes                  = db.Column(db.Text)

    def to_dict(self):
        return {
            "id":                     self.id,
            "user_id":                self.user_id,
            "date":                   self.date.isoformat(),
            "injury_type":            self.injury_type,
            "injury_severity":        self.injury_severity,
            "rehabilitation_program": self.rehabilitation_program,
            "rehabilitation_weeks":   self.rehabilitation_weeks,
            "recurrence":             self.recurrence,
            "notes":                  self.notes,
        }


class WellnessLog(db.Model):
    __tablename__ = "wellness_logs"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.String(36), nullable=False, index=True)
    date            = db.Column(db.Date, nullable=False)
    calories        = db.Column(db.Integer)
    protein_g       = db.Column(db.Float)
    carbs_g         = db.Column(db.Float)
    fat_g           = db.Column(db.Float)
    hydration_ml    = db.Column(db.Integer)
    sleep_hours     = db.Column(db.Float)
    sleep_quality   = db.Column(db.Integer)
    stress_level    = db.Column(db.Integer)
    mood_score      = db.Column(db.Integer)
    nutrition_score = db.Column(db.Float)
    notes           = db.Column(db.Text)

    def to_dict(self):
        return {
            "id":              self.id,
            "user_id":         self.user_id,
            "date":            self.date.isoformat(),
            "calories":        self.calories,
            "protein_g":       self.protein_g,
            "carbs_g":         self.carbs_g,
            "fat_g":           self.fat_g,
            "hydration_ml":    self.hydration_ml,
            "sleep_hours":     self.sleep_hours,
            "sleep_quality":   self.sleep_quality,
            "stress_level":    self.stress_level,
            "mood_score":      self.mood_score,
            "nutrition_score": self.nutrition_score,
            "notes":           self.notes,
        }
