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
    Manual FL round — a *fallback* to the automatic per-mutation training.

    Training normally runs automatically whenever data changes. Pressing this
    button only advances the round if there is **new data** for a club since its
    last round (detected via a data signature). If nothing changed, the round
    number stays the same and the caller is told so.

    - Coach: their own club.
    - Admin: the club in the body ({"club": "..."}), or all clubs if omitted.
    """
    from models import PlayerProfile, FLGlobalModel, FLClubModel
    from fl.pipeline import _do_club_update, club_data_signature

    claims   = g.claims
    roles    = claims.get("realm_access", {}).get("roles", [])
    is_admin = "admin" in roles
    body     = request.get_json(silent=True) or {}

    if is_admin:
        club = body.get("club")          # may be None -> all clubs
    else:
        club = claims.get("club") or _fetch_user_club(claims.get("sub", ""))

    if is_admin and not club:
        target_clubs = sorted({p.club for p in PlayerProfile.query.all() if p.club})
    elif club:
        target_clubs = [club] if PlayerProfile.query.filter_by(club=club).first() else []
    else:
        target_clubs = []

    if not target_clubs:
        return jsonify({
            "trained": False,
            "warning": f"No players found for {club or 'your club'}.",
        }), 200

    before = FLGlobalModel.query.order_by(FLGlobalModel.id.desc()).first()
    before_round = before.round if before else None

    updated, skipped = [], []
    for c in target_clubs:
        club_m  = FLClubModel.query.filter_by(club=c).first()
        cur_sig = club_data_signature(c)
        if club_m and club_m.data_sig == cur_sig:
            skipped.append(c)            # no new data since the last round
            continue
        try:
            if _do_club_update(c):
                updated.append(c)
            else:
                skipped.append(c)        # not enough data to train a model
        except Exception as exc:
            log.warning("[FL /train] Error for club %r: %s", c, exc)
            skipped.append(c)

    global_m = FLGlobalModel.query.order_by(FLGlobalModel.id.desc()).first()
    fl_round = global_m.round if global_m else None
    trained  = bool(updated)

    if trained:
        message = f"Round advanced to {fl_round} · trained: {', '.join(updated)}."
        warning = None
    else:
        message = "No new data since the last round — round unchanged."
        warning = message

    return jsonify({
        "trained":      trained,
        "club":         club if club else "all clubs",
        "fl_round":     fl_round,
        "before_round": before_round,
        "clubs_count":  global_m.clubs_count if global_m else None,
        "updated":      updated,
        "skipped":      skipped,
        "warning":      warning,
        "message":      message,
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

    # Model-quality metrics (accuracy / recall / loss) are restricted to admins.
    is_admin = "admin" in g.claims.get("realm_access", {}).get("roles", [])

    payload = {
        "ready":           True,
        "round":           global_m.round,
        "n_samples_total": global_m.n_samples_total,
        "clubs_count":     global_m.clubs_count,
        "updated_at":      global_m.updated_at.isoformat() if global_m.updated_at else None,
        "is_admin":        is_admin,
        "club_models": [
            {
                "club":       c.club,
                "n_samples":  c.n_samples,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in club_models
        ],
    }

    if is_admin:
        payload["accuracy"] = global_m.accuracy
        payload["recall"]   = global_m.recall
        payload["loss"]     = global_m.loss

    return jsonify(payload)


@fl_bp.get("/clubs")
@require_auth(roles=["admin"])
def fl_clubs():
    """Admin — list clubs with player counts and their last local-model state,
    so an admin can trigger an FL round per club."""
    from models import PlayerProfile, FLClubModel

    counts = {}
    for p in PlayerProfile.query.all():
        if p.club:
            counts[p.club] = counts.get(p.club, 0) + 1

    club_models = {c.club: c for c in FLClubModel.query.all()}
    result = []
    for club, n in sorted(counts.items()):
        cm = club_models.get(club)
        result.append({
            "club":       club,
            "players":    n,
            "n_samples":  cm.n_samples if cm else 0,
            "updated_at": cm.updated_at.isoformat() if cm and cm.updated_at else None,
        })
    return jsonify(result)


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
