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
        from app import models  # noqa: F401 — ensures models are registered before create_all
        db.create_all()
        _apply_migrations(db)

    return app


def _apply_migrations(db):
    """ADD COLUMN migrations for columns added after the initial schema.
    Uses IF NOT EXISTS so every startup is idempotent."""
    from sqlalchemy import text
    stmts = [
        "ALTER TABLE player_profiles ADD COLUMN IF NOT EXISTS club VARCHAR(64)",
    ]
    with db.engine.connect() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
        conn.commit()
