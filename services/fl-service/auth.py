import os, requests
from functools import wraps
from flask import request, jsonify, g
from jose import jwt, JWTError, jwk

KEYCLOAK_URL   = os.environ.get("KEYCLOAK_URL",   "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "sport-analytics")

def _get_public_keys():
    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.json()["keys"]

def _verify_token(token):
    header = jwt.get_unverified_header(token)
    keys   = _get_public_keys()
    key    = next((k for k in keys if k.get("kid") == header.get("kid")), keys[0])
    return jwt.decode(token, jwk.construct(key), algorithms=["RS256"], options={"verify_aud": False})

def require_auth(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"error": "Missing token"}), 401
            try:
                claims = _verify_token(auth.split(" ", 1)[1])
            except (JWTError, Exception) as exc:
                return jsonify({"error": "Invalid token", "detail": str(exc)}), 401
            if roles:
                user_roles = claims.get("realm_access", {}).get("roles", [])
                if not any(r in user_roles for r in roles):
                    return jsonify({"error": "Insufficient permissions"}), 403
            g.claims = claims
            return fn(*args, **kwargs)
        return wrapper
    return decorator
