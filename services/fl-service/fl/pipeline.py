"""
FL pipeline: bootstrap from Kaggle CSV + continuous per-club updates.

Bootstrap (runs once at startup):
  data.csv -> LogisticRegression on all 800 players -> saves coef/intercept
  to FLGlobalModel(round=0). This is the starting point for all clubs.

Per-club update (triggered after any data mutation):
  1. Extract (X, y) from DB for all players of that club
  2. Fine-tune local LogisticRegression starting from global weights
  3. Save club weights to FLClubModel (upsert by club name)
  4. FedAvg across ALL clubs -> new FLGlobalModel row

A threading.Lock ensures rounds are serialised — no concurrent aggregations.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

_DATA_CSV   = Path(__file__).parent.parent / "data" / "football_data.csv"
_round_lock = threading.Lock()


# ── Bootstrap ──────────────────────────────────────────────────────────────────

def bootstrap_global_model(app):
    """
    Train the initial global model on data.csv and persist it as round 0.
    No-op if a global model already exists in DB.
    """
    with app.app_context():
        from models import FLGlobalModel, db
        from fl.model import FEATURES, TARGET, preprocess, build_model, get_params
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score
        import pandas as pd

        if FLGlobalModel.query.count() > 0:
            log.info("[FL] Global model already exists (round %d) — skipping bootstrap.",
                     FLGlobalModel.query.order_by(FLGlobalModel.id.desc()).first().round)
            return

        if not _DATA_CSV.exists():
            log.warning("[FL] data.csv not found at %s — skipping bootstrap.", _DATA_CSV)
            return

        log.info("[FL] Bootstrapping global model from %s ...", _DATA_CSV)

        df = pd.read_csv(_DATA_CSV)
        df = preprocess(df)

        X = df[FEATURES].values
        y = df[TARGET].values
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.15, random_state=42, stratify=y
        )

        model = build_model()
        model.fit(X_tr, y_tr)
        acc = accuracy_score(y_te, model.predict(X_te))
        coef, intercept = get_params(model)

        record = FLGlobalModel(
            round           = 0,
            coef_json       = json.dumps(coef.tolist()),
            intercept_json  = json.dumps(intercept.tolist()),
            accuracy        = round(float(acc), 5),
            n_samples_total = int(len(y_tr)),
            clubs_count     = 0,
            updated_at      = datetime.now(timezone.utc),
        )
        db.session.add(record)
        db.session.commit()
        log.info("[FL] Bootstrap complete — accuracy=%.4f  n_train=%d", acc, len(y_tr))


# ── Per-club update ────────────────────────────────────────────────────────────

def _run_club_update(club: str, app):
    """
    Fine-tune the club's local model then re-aggregate the global model.
    Runs inside a background thread; uses _round_lock to serialise rounds.
    """
    with _round_lock:
        with app.app_context():
            _do_club_update(club)


def _do_club_update(club: str):
    from models import FLGlobalModel, FLClubModel, db
    from fl.features import extract_club_dataset
    from fl.model import build_model, get_params, set_params
    from fl.server import fed_avg
    from sklearn.metrics import accuracy_score

    # Need a global model to start from
    global_m = FLGlobalModel.query.order_by(FLGlobalModel.id.desc()).first()
    if not global_m:
        log.warning("[FL] No global model yet — bootstrap must run first.")
        return

    # Extract feature matrix for this club
    X, y = extract_club_dataset(club)
    if X is None:
        log.info("[FL] Club %r: insufficient data for local training — skipped.", club)
        return

    # Fine-tune local model starting from global weights
    g_coef      = np.array(json.loads(global_m.coef_json))
    g_intercept = np.array(json.loads(global_m.intercept_json))

    local_model = build_model()
    set_params(local_model, g_coef, g_intercept)
    local_model.fit(X, y)

    local_acc = accuracy_score(y, local_model.predict(X))
    coef, intercept = get_params(local_model)
    n = int(len(y))

    # Persist / update club model
    club_m = FLClubModel.query.filter_by(club=club).first()
    if not club_m:
        club_m = FLClubModel(club=club)
        db.session.add(club_m)
    club_m.coef_json      = json.dumps(coef.tolist())
    club_m.intercept_json = json.dumps(intercept.tolist())
    club_m.n_samples      = n
    club_m.updated_at     = datetime.now(timezone.utc)
    db.session.commit()

    log.info("[FL] Club %r local model updated — n=%d  local_acc=%.4f", club, n, local_acc)

    # FedAvg across all clubs that have contributed weights
    all_clubs = FLClubModel.query.all()
    updates = [
        (
            np.array(json.loads(c.coef_json)),
            np.array(json.loads(c.intercept_json)),
            c.n_samples,
        )
        for c in all_clubs
    ]

    new_coef, new_intercept = fed_avg(updates)
    total_n   = sum(c.n_samples for c in all_clubs)
    new_round = global_m.round + 1

    new_global = FLGlobalModel(
        round           = new_round,
        coef_json       = json.dumps(new_coef.tolist()),
        intercept_json  = json.dumps(new_intercept.tolist()),
        accuracy        = global_m.accuracy,   # bootstrap accuracy kept as reference
        n_samples_total = total_n,
        clubs_count     = len(all_clubs),
        updated_at      = datetime.now(timezone.utc),
    )
    db.session.add(new_global)
    db.session.commit()

    log.info(
        "[FL] Global model updated — round=%d  clubs=%d  total_samples=%d",
        new_round, len(all_clubs), total_n,
    )


# ── Public trigger ─────────────────────────────────────────────────────────────

def trigger_fl_update(club: str, app):
    """
    Called automatically after any data mutation (wellness / training / physical / injury).
    Schedules a background FL round for the given club.
    Returns immediately — the update runs in a daemon thread.
    """
    if not club:
        return
    t = threading.Thread(
        target=_run_club_update,
        args=(club, app),
        daemon=True,
        name=f"fl-update-{club}",
    )
    t.start()
    log.debug("[FL] Scheduled background update for club %r", club)
