import os
import time
import logging
from app import create_app

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    for attempt in range(1, 11):
        try:
            with app.app_context():
                from app.extensions import db
                db.engine.connect()
            log.info("Database connection established.")
            break
        except Exception as exc:
            log.warning("Database not ready (attempt %d/10): %s", attempt, exc)
            time.sleep(3)

    app.run(host="0.0.0.0", port=5000, debug=True)
