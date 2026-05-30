import logging
import requests
from flask import Blueprint, request, jsonify, current_app, g
from auth import require_auth

log = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

ALL_ROLES    = ("admin", "coach", "player")
PUBLIC_ROLES = ("coach", "player")


def _keycloak_url() -> str:
    return current_app.config["KEYCLOAK_URL"]

def _realm() -> str:
    return current_app.config["KEYCLOAK_REALM"]


def _admin_token() -> str:
    """Get an admin access token from the master realm."""
    resp = requests.post(
        f"{_keycloak_url()}/realms/master/protocol/openid-connect/token",
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


def _create_user_in_keycloak(username: str, email: str, password: str, role: str, club: str = None):
    """Create a Keycloak user with credentials + assign realm role. Returns (resp_dict, status_code)."""
    token   = _admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base    = f"{_keycloak_url()}/admin/realms/{_realm()}"

    # 1. Create user with credentials inline
    create_payload = {
        "username":        username,
        "email":           email,
        "firstName":       username.capitalize(),
        "lastName":        "User",
        "enabled":         True,
        "emailVerified":   True,
        "requiredActions": [],
        "credentials": [{
            "type":      "password",
            "value":     password,
            "temporary": False,
        }],
    }
    if club:
        create_payload["attributes"] = {"club": [club]}
    create_resp = requests.post(f"{base}/users", json=create_payload, headers=headers, timeout=10)
    if create_resp.status_code == 409:
        return {"error": "Username or email already exists"}, 409
    if create_resp.status_code not in (201, 204):
        return {"error": "Failed to create user", "detail": create_resp.text}, 500

    # 2. Get user ID
    users = requests.get(
        f"{base}/users?username={username}&exact=true",
        headers=headers, timeout=10,
    ).json()
    if not users:
        return {"error": "User created but could not be retrieved"}, 500
    user_id = users[0]["id"]

    # 3. Clear requiredActions; re-apply club attribute on top of whatever Keycloak stored
    full_user = requests.get(f"{base}/users/{user_id}", headers=headers, timeout=10)
    if full_user.status_code == 200:
        user_data = full_user.json()
        user_data["requiredActions"] = []
        user_data["emailVerified"]   = True
        user_data["enabled"]         = True
        if club:
            attrs = user_data.get("attributes") or {}
            attrs["club"] = [club]
            user_data["attributes"] = attrs
        put_resp = requests.put(f"{base}/users/{user_id}", json=user_data, headers=headers, timeout=10)
        if put_resp.status_code not in (200, 204) and club:
            # PUT failed — set attributes separately via a minimal payload
            requests.put(
                f"{base}/users/{user_id}",
                json={"attributes": {"club": [club]}},
                headers=headers, timeout=10,
            )

    # 4. Assign role
    role_resp = requests.get(f"{base}/roles/{role}", headers=headers, timeout=10)
    if role_resp.status_code != 200:
        return {"error": f"Role '{role}' not found in realm"}, 404
    requests.post(
        f"{base}/users/{user_id}/role-mappings/realm",
        json=[role_resp.json()],
        headers=headers,
        timeout=10,
    )

    return {"message": f"User '{username}' created with role '{role}'"}, 201


def _fetch_user_club(user_id: str):
    """Fetch the 'club' attribute directly from Keycloak admin API."""
    try:
        token   = _admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        base    = f"{_keycloak_url()}/admin/realms/{_realm()}"
        resp    = requests.get(f"{base}/users/{user_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            attrs = resp.json().get("attributes") or {}
            vals  = attrs.get("club") or []
            return vals[0] if vals else None
        log.warning("[auth] _fetch_user_club: KC returned %d for user %s", resp.status_code, user_id)
    except Exception as exc:
        log.warning("[auth] _fetch_user_club failed for %s: %s", user_id, exc)
    return None


@auth_bp.post("/register")
def register():
    """Public registration — only allows 'coach' or 'player' roles."""
    data     = request.get_json(silent=True) or {}
    required = ["username", "email", "password", "role"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400

    if data["role"] not in PUBLIC_ROLES:
        return jsonify({"error": f"role must be one of {list(PUBLIC_ROLES)}"}), 400

    try:
        body, code = _create_user_in_keycloak(
            data["username"], data["email"], data["password"], data["role"],
            club=data.get("club"),
        )
        return jsonify(body), code
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": "Unexpected error", "detail": str(exc)}), 500


@auth_bp.post("/admin/create-user")
@require_auth(roles=["admin"])
def admin_create_user():
    """Admin-only — can create users with any role (admin, coach, player)."""
    data     = request.get_json(silent=True) or {}
    required = ["username", "email", "password", "role"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400

    if data["role"] not in ALL_ROLES:
        return jsonify({"error": f"role must be one of {list(ALL_ROLES)}"}), 400

    try:
        body, code = _create_user_in_keycloak(
            data["username"], data["email"], data["password"], data["role"],
            club=data.get("club"),
        )
        return jsonify(body), code
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": "Unexpected error", "detail": str(exc)}), 500


@auth_bp.get("/me")
@require_auth()
def me():
    """Return current user info decoded from the Keycloak JWT."""
    c    = g.claims
    club = c.get("club") or _fetch_user_club(c.get("sub", ""))
    return jsonify({
        "sub":      c.get("sub"),
        "username": c.get("preferred_username"),
        "email":    c.get("email"),
        "roles":    c.get("realm_access", {}).get("roles", []),
        "club":     club,
    })
