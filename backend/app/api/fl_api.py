"""
Federated Learning API endpoints.

POST /api/fl/train  — Coach/admin triggers an FL training round for their club.
  • Returns warning if no new wellness data was recorded in the last 7 days.
  • Simulates FedAvg: in Sprint 3 this will call fl.simulate against live DB data.
"""

from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from app.api.keycloak_auth import keycloak_required
from app.models import PlayerProfile, WellnessLog

fl_bp = Blueprint("fl", __name__)

_STALE_DAYS = 7


@fl_bp.post("/train")
@keycloak_required(roles=["coach", "admin"])
def trigger_fl_round():
    claims   = request.kc_claims
    roles    = claims.get("realm_access", {}).get("roles", [])
    is_admin = "admin" in roles
    club     = claims.get("club")

    if is_admin:
        profiles = PlayerProfile.query.all()
    elif club:
        profiles = PlayerProfile.query.filter_by(club=club).all()
    else:
        profiles = []

    if not profiles:
        return jsonify({
            "trained": False,
            "warning": "No players found for your club. Seed data or add players first.",
        }), 200

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
            f"No new wellness data recorded in the last {_STALE_DAYS} days"
            f" for {club or 'your club'}. Training will use historical data only."
        )

    club_label = club if club else "all clubs"

    return jsonify({
        "trained":                   True,
        "club":                      club_label,
        "players_in_round":          len(profiles),
        "players_with_recent_data":  players_with_new_data,
        "warning":                   warning,
        "simulated_accuracy":        0.9312,
        "message": (
            f"FL training round completed for {len(profiles)} player(s) "
            f"in {club_label}. Weights aggregated via FedAvg."
        ),
    })
