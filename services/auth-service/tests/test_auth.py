from tests.conftest import auth_headers


class TestRegister:

    def test_missing_fields_rejected(self, client):
        resp = client.post("/api/auth/register", json={"username": "x"})
        assert resp.status_code == 400

    def test_admin_role_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "u", "email": "u@test.com",
            "password": "pass", "role": "admin",
        })
        assert resp.status_code == 400
        assert "role" in resp.get_json()["error"]

    def test_register_coach_calls_keycloak(self, client, mocker):
        mocker.patch("routes._create_user_in_keycloak",
                     return_value=({"message": "User 'coach2' created with role 'coach'"}, 201))
        resp = client.post("/api/auth/register", json={
            "username": "coach2", "email": "c2@test.com",
            "password": "pass123", "role": "coach",
        })
        assert resp.status_code == 201
        assert "coach2" in resp.get_json()["message"]

    def test_register_player_allowed(self, client, mocker):
        mocker.patch("routes._create_user_in_keycloak",
                     return_value=({"message": "User 'p2' created with role 'player'"}, 201))
        resp = client.post("/api/auth/register", json={
            "username": "p2", "email": "p2@test.com",
            "password": "pass", "role": "player",
        })
        assert resp.status_code == 201

    def test_duplicate_user_returns_409(self, client, mocker):
        mocker.patch("routes._create_user_in_keycloak",
                     return_value=({"error": "Username or email already exists"}, 409))
        resp = client.post("/api/auth/register", json={
            "username": "dup", "email": "dup@test.com",
            "password": "pass", "role": "coach",
        })
        assert resp.status_code == 409


class TestMe:

    def test_requires_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401
        assert "Missing token" in resp.get_json()["error"]

    def test_invalid_token_rejected(self, client, mocker):
        mocker.patch("auth._verify_token", side_effect=Exception("bad token"))
        resp = client.get("/api/auth/me", headers=auth_headers())
        assert resp.status_code == 401

    def test_returns_user_claims(self, client, mock_admin, mocker):
        mocker.patch("routes._fetch_user_club", return_value="FC Test")
        resp = client.get("/api/auth/me", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "admin1"
        assert "admin" in data["roles"]
        assert data["club"] == "FC Test"


class TestAdminCreateUser:

    def test_requires_auth(self, client):
        resp = client.post("/api/auth/admin/create-user", json={})
        assert resp.status_code == 401

    def test_player_forbidden(self, client, mock_player):
        resp = client.post("/api/auth/admin/create-user",
                           json={"username": "x", "email": "x@x.com",
                                 "password": "p", "role": "coach"},
                           headers=auth_headers())
        assert resp.status_code == 403

    def test_admin_can_create_any_role(self, client, mock_admin, mocker):
        mocker.patch("routes._create_user_in_keycloak",
                     return_value=({"message": "User 'newadmin' created with role 'admin'"}, 201))
        resp = client.post("/api/auth/admin/create-user", json={
            "username": "newadmin", "email": "na@test.com",
            "password": "pass", "role": "admin",
        }, headers=auth_headers())
        assert resp.status_code == 201

    def test_invalid_role_rejected(self, client, mock_admin):
        resp = client.post("/api/auth/admin/create-user", json={
            "username": "u", "email": "u@u.com",
            "password": "p", "role": "superuser",
        }, headers=auth_headers())
        assert resp.status_code == 400
