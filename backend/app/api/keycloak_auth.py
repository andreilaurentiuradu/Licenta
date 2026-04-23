"""
Sprint 1 — Keycloak authentication.

Endpoints:
  POST /api/auth/register  — create user in Keycloak + assign role
  GET  /api/auth/me        — return current user info from token claims

Token flow (done entirely on the frontend):
  POST http://localhost:8080/realms/sport-analytics/protocol/openid-connect/token
    grant_type=password & client_id=sport-analytics-client & username & password
  → access_token  (RS256 JWT, verified here via Keycloak JWKS)
  → refresh_token (used to get new access tokens)
"""

import requests
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from jose import jwt, JWTError, jwk

keycloak_auth_bp = Blueprint("keycloak_auth", __name__)


# ── Token verification ────────────────────────────────────────────

def _keycloak_url() -> str:
    return current_app.config["KEYCLOAK_URL"]

def _realm() -> str:
    return current_app.config["KEYCLOAK_REALM"]


def _get_public_keys() -> list:
    """Fetch JWKS from Keycloak realm."""
    url = f"{_keycloak_url()}/realms/{_realm()}/protocol/openid-connect/certs"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.json()["keys"]


def _verify_token(token: str) -> dict:
    """Verify a Keycloak RS256 JWT and return its claims."""
    header = jwt.get_unverified_header(token)
    keys   = _get_public_keys()
    key    = next((k for k in keys if k.get("kid") == header.get("kid")), keys[0])
    return jwt.decode(
        token,
        jwk.construct(key),
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def keycloak_required(roles: list = None):
    """Decorator: validate Keycloak token + optional role check."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"error": "Missing token"}), 401
            try:
                claims = _verify_token(auth.split(" ", 1)[1])
            except (JWTError, Exception) as exc:
                return jsonify({"error": "Invalid or expired token", "detail": str(exc)}), 401

            if roles:
                user_roles = claims.get("realm_access", {}).get("roles", [])
                if not any(r in user_roles for r in roles):
                    return jsonify({"error": "Insufficient permissions"}), 403

            request.kc_claims = claims
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── Admin helper ──────────────────────────────────────────────────

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


# ── Routes ────────────────────────────────────────────────────────

@keycloak_auth_bp.post("/register")
def register():
    """Create a new user in Keycloak and assign an admin or coach role."""
    data     = request.get_json(silent=True) or {}
    required = ["username", "email", "password", "role"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400

    role = data["role"]
    if role not in ("admin", "coach"):
        return jsonify({"error": "role must be 'admin' or 'coach'"}), 400

    try:
        token   = _admin_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        realm   = _realm()
        base    = f"{_keycloak_url()}/admin/realms/{realm}"

        # 1. Create user with credentials inline (like realm-export does)
        create_payload = {
            "username":        data["username"],
            "email":           data["email"],
            "firstName":       data["username"].capitalize(),
            "lastName":        "User",
            "enabled":         True,
            "emailVerified":   True,
            "requiredActions": [],
            "credentials": [{
                "type":      "password",
                "value":     data["password"],
                "temporary": False,
            }],
        }
        create_resp = requests.post(f"{base}/users", json=create_payload, headers=headers, timeout=10)
        if create_resp.status_code == 409:
            return jsonify({"error": "Username or email already exists"}), 409
        if create_resp.status_code not in (201, 204):
            return jsonify({"error": "Failed to create user", "detail": create_resp.text}), 500

        # 2. Get user ID
        users = requests.get(
            f"{base}/users?username={data['username']}&exact=true",
            headers=headers, timeout=10,
        ).json()
        if not users:
            return jsonify({"error": "User created but could not be retrieved"}), 500
        user_id = users[0]["id"]

        # 3. Force-clear requiredActions with full PUT (safeguard against auto-added actions)
        full_user = requests.get(f"{base}/users/{user_id}", headers=headers, timeout=10).json()
        full_user["requiredActions"] = []
        full_user["emailVerified"]   = True
        full_user["enabled"]         = True
        requests.put(f"{base}/users/{user_id}", json=full_user, headers=headers, timeout=10)

        # 4. Assign role
        role_resp = requests.get(f"{base}/roles/{role}", headers=headers, timeout=10)
        if role_resp.status_code != 200:
            return jsonify({"error": f"Role '{role}' not found in realm"}), 404
        requests.post(
            f"{base}/users/{user_id}/role-mappings/realm",
            json=[role_resp.json()],
            headers=headers,
            timeout=10,
        )

        return jsonify({"message": f"User '{data['username']}' created with role '{role}'"}), 201

    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": "Unexpected error", "detail": str(exc)}), 500


@keycloak_auth_bp.get("/me")
@keycloak_required()
def me():
    """Return current user info decoded from the Keycloak JWT."""
    c = request.kc_claims
    return jsonify({
        "sub":      c.get("sub"),
        "username": c.get("preferred_username"),
        "email":    c.get("email"),
        "roles":    c.get("realm_access", {}).get("roles", []),
    })
