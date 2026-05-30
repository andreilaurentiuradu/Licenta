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
app.config["KEYCLOAK_URL"]                   = os.environ.get("KEYCLOAK_URL",   "http://keycloak:8080")
app.config["KEYCLOAK_REALM"]                 = os.environ.get("KEYCLOAK_REALM", "lawranalyzer")
app.config["GROQ_API_KEY"]                   = os.environ.get("GROQ_API_KEY",   "")

from models import db
db.init_app(app)

from routes import ai_bp
app.register_blueprint(ai_bp, url_prefix="/api/players")


def _init_db():
    for attempt in range(30):
        try:
            with app.app_context():
                db.create_all()
            log.info("[ai-recommendation-service] DB initialised.")
            return
        except Exception as exc:
            log.warning("[ai-recommendation-service] DB not ready (attempt %d/30): %s", attempt + 1, exc)
            time.sleep(3)
    log.error("[ai-recommendation-service] Could not connect to DB after 30 attempts.")


threading.Thread(target=_init_db, daemon=True, name="db-init").start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)
