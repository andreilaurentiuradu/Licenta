import threading
from flask import Flask
from flask_cors import CORS
from config import config
from app.extensions import db


def create_app(env_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[env_name])

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)

    from app.api.keycloak_auth import keycloak_auth_bp
    from app.api.feedback import feedback_bp
    from app.api.players import players_bp
    from app.api.fl_api import fl_bp

    app.register_blueprint(keycloak_auth_bp, url_prefix="/api/auth")
    app.register_blueprint(feedback_bp,      url_prefix="/api/feedback")
    app.register_blueprint(players_bp,       url_prefix="/api/players")
    app.register_blueprint(fl_bp,            url_prefix="/api/fl")

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()
        _apply_migrations(db)

    # Bootstrap the global FL model from data.csv in a background thread
    # so startup is not blocked even if the CSV is large.
    t = threading.Thread(target=_bootstrap_fl, args=(app,), daemon=True)
    t.start()

    return app


def _apply_migrations(db):
    """Idempotent ADD COLUMN statements for schema changes after initial create_all."""
    from sqlalchemy import text
    stmts = [
        "ALTER TABLE player_profiles       ADD COLUMN IF NOT EXISTS club VARCHAR(64)",
        # TrainingLog new field
        "ALTER TABLE training_logs         ADD COLUMN IF NOT EXISTS warmup_adherence FLOAT",
        # PhysicalAssessment new fields
        "ALTER TABLE physical_assessments  ADD COLUMN IF NOT EXISTS balance_test_score FLOAT",
        "ALTER TABLE physical_assessments  ADD COLUMN IF NOT EXISTS sprint_speed_10m_s FLOAT",
        "ALTER TABLE physical_assessments  ADD COLUMN IF NOT EXISTS agility_score FLOAT",
        # WellnessLog derived nutrition score
        "ALTER TABLE wellness_logs         ADD COLUMN IF NOT EXISTS nutrition_score FLOAT",
    ]
    with db.engine.connect() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
        conn.commit()


def _bootstrap_fl(app):
    """Train initial global model from data.csv if none exists yet."""
    try:
        from fl.pipeline import bootstrap_global_model
        bootstrap_global_model(app)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("[FL] Bootstrap error: %s", exc)
