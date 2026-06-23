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
# Validate pooled connections before use so a stale one (after Postgres restart
# or idle) is transparently replaced instead of raising "server closed the
# connection unexpectedly" on the first request.
app.config["SQLALCHEMY_ENGINE_OPTIONS"]      = {"pool_pre_ping": True, "pool_recycle": 280}
app.config["KEYCLOAK_URL"]                   = os.environ.get("KEYCLOAK_URL",   "http://keycloak:8080")
app.config["KEYCLOAK_REALM"]                 = os.environ.get("KEYCLOAK_REALM", "lawranalyzer")
app.config["KEYCLOAK_ADMIN_USER"]            = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
app.config["KEYCLOAK_ADMIN_PASS"]            = os.environ.get("KEYCLOAK_ADMIN_PASS", "admin123")

from models import db
db.init_app(app)

from routes import players_bp
app.register_blueprint(players_bp, url_prefix="/api/players")


def _apply_migrations():
    from sqlalchemy import text
    stmts = [
        "ALTER TABLE player_profiles       ADD COLUMN IF NOT EXISTS club VARCHAR(64)",
        "ALTER TABLE training_logs         ADD COLUMN IF NOT EXISTS warmup_adherence FLOAT",
        "ALTER TABLE physical_assessments  ADD COLUMN IF NOT EXISTS balance_test_score FLOAT",
        "ALTER TABLE physical_assessments  ADD COLUMN IF NOT EXISTS sprint_speed_10m_s FLOAT",
        "ALTER TABLE physical_assessments  ADD COLUMN IF NOT EXISTS agility_score FLOAT",
        "ALTER TABLE wellness_logs         ADD COLUMN IF NOT EXISTS nutrition_score FLOAT",
    ]
    with db.engine.connect() as conn:
        for s in stmts:
            conn.execute(text(s))
        conn.commit()


def _init_db():
    for attempt in range(30):
        try:
            with app.app_context():
                db.create_all()
                _apply_migrations()
            log.info("[player-service] DB initialised.")
            return
        except Exception as exc:
            log.warning("[player-service] DB not ready (attempt %d/30): %s", attempt + 1, exc)
            time.sleep(3)
    log.error("[player-service] Could not connect to DB after 30 attempts.")


threading.Thread(target=_init_db, daemon=True, name="db-init").start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
