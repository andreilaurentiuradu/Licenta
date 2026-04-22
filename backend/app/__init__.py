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

    app.register_blueprint(keycloak_auth_bp, url_prefix="/api/auth")
    app.register_blueprint(feedback_bp,      url_prefix="/api/feedback")

    with app.app_context():
        from app import models  # noqa: F401 — ensures models are registered before create_all
        db.create_all()

    return app
