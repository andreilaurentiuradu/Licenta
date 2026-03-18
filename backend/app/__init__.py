import os
from flask import Flask
from flask_cors import CORS
from config import config
from app.extensions import db, jwt, migrate


def create_app(env_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[env_name])

    # Ensure instance directories exist
    os.makedirs(app.config["MODEL_DIR"], exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(app.config["MODEL_DIR"])), exist_ok=True)

    # Extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from app.api.auth import auth_bp
    from app.api.teams import teams_bp
    from app.api.players import players_bp
    from app.api.predictions import predictions_bp
    from app.api.federation import federation_bp
    from app.api.analytics import analytics_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(teams_bp, url_prefix="/api/teams")
    app.register_blueprint(players_bp, url_prefix="/api/players")
    app.register_blueprint(predictions_bp, url_prefix="/api/predictions")
    app.register_blueprint(federation_bp, url_prefix="/api/federation")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

    return app
