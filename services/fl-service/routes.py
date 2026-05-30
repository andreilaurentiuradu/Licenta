import logging
import requests as req
from datetime import date, timedelta, datetime, timezone

from flask import Blueprint, request, jsonify, g, current_app
from auth import require_auth

fl_bp       = Blueprint("fl", __name__)
internal_bp = Blueprint("fl_internal", __name__)

log = logging.getLogger(__name__)

_STALE_DAYS = 7


def _admin_token() -> str:
    resp = req.post(
        f"{current_app.config['KEYCLOAK_URL']}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id":  "admin-cli",
            "username":   current_app.config["KEYCLOAK_ADMIN_USER"],
            "password":   current_app.config["KEYCLOAK_ADMIN_PASS"],
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Keycloak admin auth failed: {resp.text}")
    return resp.json()["access_token"]


def _fetch_user_club(user_id: str):
    """Fetch the 'club' attribute directly from Keycloak."""
    try:
        token   = _admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        base    = f"{current_app.config['KEYCLOAK_URL']}/admin/realms/{current_app.config['KEYCLOAK_REALM']}"
        resp    = req.get(f"{base}/users/{user_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            attrs = resp.json().get("attributes") or {}
            vals  = attrs.get("club") or []
            return vals[0] if vals else None
    except Exception:
        pass
    return None


@fl_bp.post("/train")
@require_auth(roles=["coach", "admin"])
def trigger_fl_round():
    """
    Manually trigger an FL update round for the coach's club.
    """
    from models import PlayerProfile, WellnessLog, FLGlobalModel, FLClubModel

    claims   = g.claims
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
    trained     = False
    accuracy    = None
    fl_round    = None
    clubs_count = None

    try:
        from fl.pipeline import _do_club_update
        if is_admin:
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
        log.warning("[FL /train] Error: %s", exc)

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
@require_auth(roles=["coach", "admin"])
def fl_status():
    """Return current global model statistics."""
    from models import FLGlobalModel, FLClubModel

    global_m = FLGlobalModel.query.order_by(FLGlobalModel.id.desc()).first()

    if not global_m:
        return jsonify({
            "ready":   False,
            "message": "Global model not trained yet. Place football_data.csv in datasets/ and rebuild.",
        })

    club_models = FLClubModel.query.order_by(FLClubModel.updated_at.desc()).all()

    return jsonify({
        "ready":           True,
        "round":           global_m.round,
        "accuracy":        global_m.accuracy,
        "n_samples_total": global_m.n_samples_total,
        "clubs_count":     global_m.clubs_count,
        "updated_at":      global_m.updated_at.isoformat() if global_m.updated_at else None,
        "club_models": [
            {
                "club":       c.club,
                "n_samples":  c.n_samples,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in club_models
        ],
    })


@fl_bp.get("/risk")
@require_auth(roles=["coach", "admin"])
def club_risk_ranking():
    """
    Return injury risk scores for all players in the coach's club,
    sorted by probability descending. Admins can pass ?club=<name>.
    """
    from models import PlayerProfile
    from fl.features import predict_injury_risk

    claims   = g.claims
    roles    = claims.get("realm_access", {}).get("roles", [])
    is_admin = "admin" in roles

    if is_admin:
        club = request.args.get("club")
        profiles = (PlayerProfile.query.filter_by(club=club).all()
                    if club else PlayerProfile.query.all())
    else:
        club = claims.get("club") or _fetch_user_club(claims.get("sub", ""))
        if not club:
            return jsonify([])
        profiles = PlayerProfile.query.filter_by(club=club).all()

    results = []
    for p in profiles:
        risk_data = predict_injury_risk(p.user_id)
        results.append({
            "user_id":     p.user_id,
            "username":    p.username,
            "club":        p.club,
            "position":    p.position,
            "risk":        risk_data["risk"],
            "probability": risk_data["probability"],
        })

    results.sort(key=lambda x: x["probability"], reverse=True)
    return jsonify(results)


@internal_bp.get("/risk/<user_id>")
def internal_risk(user_id):
    """Return FL injury risk for a single player (internal, no auth)."""
    from fl.features import predict_injury_risk
    try:
        return jsonify(predict_injury_risk(user_id))
    except Exception as exc:
        log.warning("[FL] internal_risk error for %s: %s", user_id, exc)
        return jsonify({"risk": "low", "probability": 0.0})


@internal_bp.post("/trigger")
def internal_trigger():
    """
    Internal endpoint called by player-service after data mutations.
    No auth required — accessible only on internal Docker network.
    Registered under /internal/trigger on the fl-service.
    """
    data = request.get_json(silent=True) or {}
    club = data.get("club")
    if not club:
        return jsonify({"error": "club is required"}), 400

    try:
        from flask import current_app
        from fl.pipeline import trigger_fl_update
        trigger_fl_update(club, current_app._get_current_object())
        return jsonify({"scheduled": True, "club": club})
    except Exception as exc:
        log.warning("[FL] internal_trigger error: %s", exc)
        return jsonify({"scheduled": False, "error": str(exc)}), 500
