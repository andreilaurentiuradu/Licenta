import responses
from tests.conftest import ADMIN_CLAIMS, COACH_CLAIMS, auth_headers


KC = "http://keycloak:8080/admin/realms/sport-analytics"


def _stub_successful_user_creation(username="newuser", role="coach"):
    """Register common Keycloak admin API responses for a successful user creation."""
    responses.add(responses.POST, f"{KC}/users", status=201)
    responses.add(
        responses.GET,
        f"{KC}/users",
        json=[{"id": "new-user-uuid", "username": username, "requiredActions": []}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{KC}/users/new-user-uuid",
        json={"id": "new-user-uuid", "username": username, "requiredActions": []},
        status=200,
    )
    responses.add(responses.PUT, f"{KC}/users/new-user-uuid", status=204)
    responses.add(responses.GET, f"{KC}/roles/{role}", json={"name": role, "id": f"role-{role}"}, status=200)
    responses.add(responses.POST, f"{KC}/users/new-user-uuid/role-mappings/realm", status=204)


# ── Public /register ───────────────────────────────────────────────

class TestPublicRegister:

    def test_missing_fields_returns_400(self, client):
        resp = client.post("/api/auth/register", json={"username": "x"})
        assert resp.status_code == 400
        assert "Required fields" in resp.get_json()["error"]

    def test_admin_role_rejected_from_public(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "x", "email": "x@x.ro", "password": "secret123", "role": "admin",
        })
        assert resp.status_code == 400
        assert "coach" in resp.get_json()["error"]
        assert "player" in resp.get_json()["error"]

    def test_unknown_role_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "x", "email": "x@x.ro", "password": "secret123", "role": "superuser",
        })
        assert resp.status_code == 400

    @responses.activate
    def test_coach_registration_success(self, client, mock_admin_token):
        _stub_successful_user_creation(username="laur", role="coach")
        resp = client.post("/api/auth/register", json={
            "username": "laur", "email": "laur@x.ro", "password": "secret123", "role": "coach",
        })
        assert resp.status_code == 201
        assert "coach" in resp.get_json()["message"]

    @responses.activate
    def test_player_registration_success(self, client, mock_admin_token):
        _stub_successful_user_creation(username="marian", role="player")
        resp = client.post("/api/auth/register", json={
            "username": "marian", "email": "marian@x.ro", "password": "secret123", "role": "player",
        })
        assert resp.status_code == 201
        assert "player" in resp.get_json()["message"]

    @responses.activate
    def test_duplicate_user_returns_409(self, client, mock_admin_token):
        responses.add(responses.POST, f"{KC}/users", status=409)
        resp = client.post("/api/auth/register", json={
            "username": "existing", "email": "e@x.ro", "password": "secret123", "role": "coach",
        })
        assert resp.status_code == 409

    @responses.activate
    def test_keycloak_failure_returns_500(self, client, mock_admin_token):
        responses.add(responses.POST, f"{KC}/users", status=500, body="Boom")
        resp = client.post("/api/auth/register", json={
            "username": "u", "email": "u@x.ro", "password": "secret123", "role": "coach",
        })
        assert resp.status_code == 500


# ── Admin-only /admin/create-user ─────────────────────────────────

class TestAdminCreateUser:

    def test_requires_token(self, client):
        resp = client.post("/api/auth/admin/create-user", json={
            "username": "x", "email": "x@x.ro", "password": "secret123", "role": "admin",
        })
        assert resp.status_code == 401

    def test_non_admin_rejected(self, client, mock_verify_token):
        mock_verify_token(COACH_CLAIMS)
        resp = client.post(
            "/api/auth/admin/create-user",
            json={"username": "x", "email": "x@x.ro", "password": "secret123", "role": "admin"},
            headers=auth_headers(),
        )
        assert resp.status_code == 403

    @responses.activate
    def test_admin_can_create_admin(self, client, mock_admin_token, mock_verify_token):
        mock_verify_token(ADMIN_CLAIMS)
        _stub_successful_user_creation(username="newadmin", role="admin")
        resp = client.post(
            "/api/auth/admin/create-user",
            json={"username": "newadmin", "email": "a@x.ro", "password": "secret123", "role": "admin"},
            headers=auth_headers(),
        )
        assert resp.status_code == 201
        assert "admin" in resp.get_json()["message"]

    @responses.activate
    def test_admin_can_create_coach(self, client, mock_admin_token, mock_verify_token):
        mock_verify_token(ADMIN_CLAIMS)
        _stub_successful_user_creation(username="newcoach", role="coach")
        resp = client.post(
            "/api/auth/admin/create-user",
            json={"username": "newcoach", "email": "c@x.ro", "password": "secret123", "role": "coach"},
            headers=auth_headers(),
        )
        assert resp.status_code == 201

    def test_invalid_role_rejected(self, client, mock_verify_token):
        mock_verify_token(ADMIN_CLAIMS)
        resp = client.post(
            "/api/auth/admin/create-user",
            json={"username": "x", "email": "x@x.ro", "password": "secret123", "role": "ghost"},
            headers=auth_headers(),
        )
        assert resp.status_code == 400
