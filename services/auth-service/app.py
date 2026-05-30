import os
from flask import Flask
from flask_cors import CORS
from routes import auth_bp

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config["KEYCLOAK_URL"]        = os.environ.get("KEYCLOAK_URL",        "http://keycloak:8080")
app.config["KEYCLOAK_REALM"]      = os.environ.get("KEYCLOAK_REALM",      "lawranalyzer")
app.config["KEYCLOAK_ADMIN_USER"] = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
app.config["KEYCLOAK_ADMIN_PASS"] = os.environ.get("KEYCLOAK_ADMIN_PASS", "admin123")
app.register_blueprint(auth_bp, url_prefix="/api/auth")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
