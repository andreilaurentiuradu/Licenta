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
app.config["KEYCLOAK_URL"]                   = os.environ.get("KEYCLOAK_URL",        "http://keycloak:8080")
app.config["KEYCLOAK_REALM"]                 = os.environ.get("KEYCLOAK_REALM",      "lawranalyzer")
app.config["KEYCLOAK_ADMIN_USER"]            = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
app.config["KEYCLOAK_ADMIN_PASS"]            = os.environ.get("KEYCLOAK_ADMIN_PASS", "admin123")

from sqlalchemy import text

from models import db
db.init_app(app)

from routes import fl_bp, internal_bp
app.register_blueprint(fl_bp, url_prefix="/api/fl")
app.register_blueprint(internal_bp, url_prefix="/internal")

# Idempotent migrations for columns added after the table already exists
# (create_all never alters an existing table).
_MIGRATIONS = [
    "ALTER TABLE fl_global_models ADD COLUMN IF NOT EXISTS recall DOUBLE PRECISION",
    "ALTER TABLE fl_global_models ADD COLUMN IF NOT EXISTS loss   DOUBLE PRECISION",
    "ALTER TABLE fl_club_models   ADD COLUMN IF NOT EXISTS data_sig VARCHAR(128)",
]


def _ensure_columns():
    with app.app_context():
        for stmt in _MIGRATIONS:
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                log.warning("[fl-service] Migration skipped (%s): %s", stmt, exc)


def _init_db_then_bootstrap():
    for attempt in range(30):
        try:
            with app.app_context():
                db.create_all()
            log.info("[fl-service] DB initialised.")
            break
        except Exception as exc:
            log.warning("[fl-service] DB not ready (attempt %d/30): %s", attempt + 1, exc)
            time.sleep(3)
    else:
        log.error("[fl-service] Could not connect to DB after 30 attempts.")
        return

    _ensure_columns()
    from fl.pipeline import bootstrap_global_model
    bootstrap_global_model(app)


threading.Thread(target=_init_db_then_bootstrap, daemon=True, name="fl-init").start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
