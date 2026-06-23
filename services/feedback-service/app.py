import os
import threading
import time
import logging

from flask import Flask
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config["SQLALCHEMY_DATABASE_URI"]        = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Validate pooled connections before use (avoids stale-connection 500s).
app.config["SQLALCHEMY_ENGINE_OPTIONS"]      = {"pool_pre_ping": True, "pool_recycle": 280}
app.config["KEYCLOAK_URL"]                   = os.environ.get("KEYCLOAK_URL",   "http://keycloak:8080")
app.config["KEYCLOAK_REALM"]                 = os.environ.get("KEYCLOAK_REALM", "lawranalyzer")

from models import db
db.init_app(app)

from routes import feedback_bp
app.register_blueprint(feedback_bp, url_prefix="/api/feedback")


def _init_db():
    for attempt in range(30):
        try:
            with app.app_context():
                db.create_all()
            log.info("[feedback-service] DB initialised.")
            return
        except Exception as exc:
            log.warning("[feedback-service] DB not ready (attempt %d/30): %s", attempt + 1, exc)
            time.sleep(3)
    log.error("[feedback-service] Could not connect to DB after 30 attempts.")


threading.Thread(target=_init_db, daemon=True, name="db-init").start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
