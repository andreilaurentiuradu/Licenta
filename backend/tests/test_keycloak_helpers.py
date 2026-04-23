import responses
from app.api.keycloak_auth import _create_user_in_keycloak, PUBLIC_ROLES, ALL_ROLES


KC = "http://keycloak:8080/admin/realms/sport-analytics"


class TestRoleConstants:

    def test_public_roles(self):
        assert "coach"  in PUBLIC_ROLES
        assert "player" in PUBLIC_ROLES
        assert "admin" not in PUBLIC_ROLES

    def test_all_roles(self):
        assert set(ALL_ROLES) == {"admin", "coach", "player"}


class TestCreateUserHelper:

    def _stub_keycloak(self, username, role):
        responses.add(responses.POST, f"{KC}/users", status=201)
        responses.add(
            responses.GET,
            f"{KC}/users",
            json=[{"id": "uid-1", "username": username, "requiredActions": []}],
            status=200,
        )
        responses.add(
            responses.GET,
            f"{KC}/users/uid-1",
            json={"id": "uid-1", "username": username, "requiredActions": []},
            status=200,
        )
        responses.add(responses.PUT, f"{KC}/users/uid-1", status=204)
        responses.add(responses.GET, f"{KC}/roles/{role}", json={"name": role, "id": f"role-{role}"}, status=200)
        responses.add(responses.POST, f"{KC}/users/uid-1/role-mappings/realm", status=204)

    @responses.activate
    def test_create_coach_success(self, app, mock_admin_token):
        self._stub_keycloak("alice", "coach")
        with app.app_context():
            body, code = _create_user_in_keycloak("alice", "alice@x.ro", "secret123", "coach")
        assert code == 201
        assert "alice" in body["message"]
        assert "coach" in body["message"]

    @responses.activate
    def test_conflict_returns_409(self, app, mock_admin_token):
        responses.add(responses.POST, f"{KC}/users", status=409)
        with app.app_context():
            body, code = _create_user_in_keycloak("dupe", "d@x.ro", "secret123", "coach")
        assert code == 409

    @responses.activate
    def test_creation_failure_returns_500(self, app, mock_admin_token):
        responses.add(responses.POST, f"{KC}/users", status=500, body="oops")
        with app.app_context():
            body, code = _create_user_in_keycloak("u", "u@x.ro", "secret123", "coach")
        assert code == 500

    @responses.activate
    def test_missing_role_returns_404(self, app, mock_admin_token):
        responses.add(responses.POST, f"{KC}/users", status=201)
        responses.add(
            responses.GET,
            f"{KC}/users",
            json=[{"id": "uid-1", "username": "u", "requiredActions": []}],
            status=200,
        )
        responses.add(
            responses.GET,
            f"{KC}/users/uid-1",
            json={"id": "uid-1", "requiredActions": []},
            status=200,
        )
        responses.add(responses.PUT, f"{KC}/users/uid-1", status=204)
        responses.add(responses.GET, f"{KC}/roles/ghost", status=404)
        with app.app_context():
            body, code = _create_user_in_keycloak("u", "u@x.ro", "secret123", "ghost")
        assert code == 404

    @responses.activate
    def test_payload_sent_to_keycloak_is_correct(self, app, mock_admin_token):
        self._stub_keycloak("laur", "player")
        with app.app_context():
            _create_user_in_keycloak("laur", "laur@x.ro", "parola12", "player")

        create_call = responses.calls[0]
        import json
        body = json.loads(create_call.request.body)
        assert body["username"]        == "laur"
        assert body["email"]           == "laur@x.ro"
        assert body["enabled"]         is True
        assert body["emailVerified"]   is True
        assert body["requiredActions"] == []
        assert body["credentials"][0]["value"]     == "parola12"
        assert body["credentials"][0]["temporary"] is False
