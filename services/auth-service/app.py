import os
import threading
import time
import logging

from flask import Flask
from flask_cors import CORS
from routes import auth_bp, ensure_unmanaged_attributes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config["KEYCLOAK_URL"]        = os.environ.get("KEYCLOAK_URL",        "http://keycloak:8080")
app.config["KEYCLOAK_REALM"]      = os.environ.get("KEYCLOAK_REALM",      "lawranalyzer")
app.config["KEYCLOAK_ADMIN_USER"] = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
app.config["KEYCLOAK_ADMIN_PASS"] = os.environ.get("KEYCLOAK_ADMIN_PASS", "admin123")
app.register_blueprint(auth_bp, url_prefix="/api/auth")


def _bootstrap_keycloak():
    """Wait for Keycloak to be ready, then ensure custom attributes persist."""
    for attempt in range(30):
        try:
            with app.app_context():
                ensure_unmanaged_attributes()
            return
        except Exception as exc:
            log.warning("[auth] Keycloak not ready (attempt %d/30): %s", attempt + 1, exc)
            time.sleep(4)
    log.error("[auth] Could not configure Keycloak user profile after 30 attempts.")


if os.environ.get("AUTH_KC_BOOTSTRAP", "1") == "1":
    threading.Thread(target=_bootstrap_keycloak, daemon=True, name="kc-bootstrap").start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
