from flask import Flask
from flask_cors import CORS
from config import config


def create_app(env_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[env_name])

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from app.api.keycloak_auth import keycloak_auth_bp
    app.register_blueprint(keycloak_auth_bp, url_prefix="/api/auth")

    return app
