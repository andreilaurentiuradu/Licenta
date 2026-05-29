"""
Federated Learning API.

POST /api/fl/train   — Coach/admin triggers an FL round for their club.
GET  /api/fl/status  — Returns current global model stats (round, accuracy, clubs).
"""

from datetime import date, timedelta, datetime, timezone
from flask import Blueprint, request, jsonify
from app.api.keycloak_auth import keycloak_required, _fetch_user_club
from app.models import PlayerProfile, WellnessLog, FLGlobalModel, FLClubModel

fl_bp = Blueprint("fl", __name__)

_STALE_DAYS = 7


@fl_bp.post("/train")
@keycloak_required(roles=["coach", "admin"])
def trigger_fl_round():
    """
    Manually trigger an FL update round for the coach's club.
    The pipeline also runs automatically on every data mutation,
    so this endpoint is provided as an explicit override.
    """
    claims   = request.kc_claims
    roles    = claims.get("realm_access", {}).get("roles", [])
    is_admin = "admin" in roles
    club     = claims.get("club")
    if not is_admin and not club:
        club = _fetch_user_club(claims.get("sub", ""))

    if is_admin:
        profiles = PlayerProfile.query.all()
    elif club:
        profiles = PlayerProfile.query.filter_by(club=club).all()
    else:
        profiles = []

    if not profiles:
        return jsonify({
            "trained": False,
            "warning": "No players found for your club.",
        }), 200

    # Stale-data check
    cutoff = date.today() - timedelta(days=_STALE_DAYS)
    players_with_new_data = sum(
        1 for p in profiles
        if WellnessLog.query.filter(
            WellnessLog.user_id == p.user_id,
            WellnessLog.date    >= cutoff,
        ).count() > 0
    )

    warning = None
    if players_with_new_data == 0:
        warning = (
            f"No new wellness data in the last {_STALE_DAYS} days "
            f"for {club or 'your club'}. Training on historical data only."
        )

    # Run real FL update
    trained = False
    accuracy = None
    fl_round = None
    clubs_count = None

    try:
        from flask import current_app
        from fl.pipeline import _do_club_update  # synchronous — runs in request thread
        clubs_to_train = [c.club for c in FLClubModel.query.all()]
        if is_admin:
            # Admin triggers all clubs
            all_clubs = list({p.club for p in profiles if p.club})
            for c in all_clubs:
                _do_club_update(c)
        elif club:
            _do_club_update(club)

        global_m = FLGlobalModel.query.order_by(FLGlobalModel.id.desc()).first()
        if global_m:
            trained     = True
            accuracy    = global_m.accuracy
            fl_round    = global_m.round
            clubs_count = global_m.clubs_count
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("[FL /train] Error: %s", exc)

    club_label = club if club else "all clubs"
    return jsonify({
        "trained":                  trained,
        "club":                     club_label,
        "players_in_round":         len(profiles),
        "players_with_recent_data": players_with_new_data,
        "warning":                  warning,
        "fl_round":                 fl_round,
        "global_accuracy":          accuracy,
        "clubs_count":              clubs_count,
        "message": (
            f"FL round completed for {len(profiles)} player(s) in {club_label}. "
            "Weights aggregated via FedAvg."
        ) if trained else "FL update skipped — insufficient data.",
    })


@fl_bp.get("/status")
@keycloak_required(roles=["coach", "admin"])
def fl_status():
    """Return current global model statistics."""
    global_m = FLGlobalModel.query.order_by(FLGlobalModel.id.desc()).first()

    if not global_m:
        return jsonify({
            "ready":        False,
            "message":      "Global model not trained yet. Place data.csv in backend/models/ and restart.",
        })

    club_models = FLClubModel.query.order_by(FLClubModel.updated_at.desc()).all()

    return jsonify({
        "ready":            True,
        "round":            global_m.round,
        "accuracy":         global_m.accuracy,
        "n_samples_total":  global_m.n_samples_total,
        "clubs_count":      global_m.clubs_count,
        "updated_at":       global_m.updated_at.isoformat() if global_m.updated_at else None,
        "club_models": [
            {
                "club":       c.club,
                "n_samples":  c.n_samples,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in club_models
        ],
    })
