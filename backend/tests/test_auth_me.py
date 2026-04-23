from tests.conftest import COACH_CLAIMS, ADMIN_CLAIMS, PLAYER_CLAIMS, auth_headers


class TestMeEndpoint:

    def test_requires_authorization_header(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401
        assert "Missing token" in resp.get_json()["error"]

    def test_invalid_token_rejected(self, client, mocker):
        mocker.patch(
            "app.api.keycloak_auth._verify_token",
            side_effect=Exception("invalid signature"),
        )
        resp = client.get("/api/auth/me", headers=auth_headers("bad-token"))
        assert resp.status_code == 401
        assert "Invalid or expired token" in resp.get_json()["error"]

    def test_returns_coach_claims(self, client, mock_verify_token):
        mock_verify_token(COACH_CLAIMS)
        resp = client.get("/api/auth/me", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "coach_user"
        assert data["email"]    == "coach@sport.local"
        assert data["roles"]    == ["coach"]

    def test_returns_admin_claims(self, client, mock_verify_token):
        mock_verify_token(ADMIN_CLAIMS)
        resp = client.get("/api/auth/me", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.get_json()["roles"] == ["admin"]

    def test_returns_player_claims(self, client, mock_verify_token):
        mock_verify_token(PLAYER_CLAIMS)
        resp = client.get("/api/auth/me", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.get_json()["roles"] == ["player"]
