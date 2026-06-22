import pytest
from tests.conftest import auth_headers, PLAYER_UID, PLAYER2_UID

FL_RISK_LOW  = {"risk": "low",  "probability": 0.04}
FL_RISK_HIGH = {"risk": "high", "probability": 0.97}


@pytest.fixture(autouse=True)
def mock_fl_risk(mocker):
    """Silence the HTTP call to fl-service in every test."""
    return mocker.patch("routes._fetch_fl_risk", return_value=FL_RISK_LOW)


class TestGetRecommendations:

    def test_requires_auth(self, client):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations")
        assert resp.status_code == 401

    def test_player_cannot_access_other_player(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER2_UID}/recommendations", headers=auth_headers())
        assert resp.status_code == 403

    def test_player_can_access_own(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers())
        assert resp.status_code == 200

    def test_coach_can_access_any_player(self, client, mock_coach):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers())
        assert resp.status_code == 200

    def test_first_visit_generates_defaults(self, client, mock_player):
        data = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        assert data["ai_enabled"] is False
        assert len(data["active"]) >= 1
        assert data["completed"] == []

    def test_response_has_required_fields(self, client, mock_player):
        data = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        for key in ("injury_risk", "fl_probability", "ai_enabled", "active", "completed"):
            assert key in data

    def test_active_recommendation_structure(self, client, mock_player):
        data = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        for rec in data["active"]:
            assert {"id", "category", "priority", "text", "status"} <= set(rec.keys())
            assert rec["status"] == "pending"

    def test_injury_risk_comes_from_fl_model(self, client, mock_player, mocker):
        mocker.patch("routes._fetch_fl_risk", return_value=FL_RISK_HIGH)
        data = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        assert data["injury_risk"] == "high"
        assert data["fl_probability"] == 0.97

    def test_does_not_regenerate_on_second_visit(self, client, mock_player):
        first  = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        second = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        assert sorted(r["id"] for r in first["active"]) == sorted(r["id"] for r in second["active"])

    def test_uses_groq_when_key_present(self, client, mock_player, app, mocker):
        app.config["GROQ_API_KEY"] = "test-key"
        mock_ai = mocker.patch("routes._call_openai", return_value={
            "recommendations": [
                {"category": "Recovery", "priority": "high", "text": "Test recommendation."},
            ],
        })
        data = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        assert data["ai_enabled"] is True
        assert any(r["text"] == "Test recommendation." for r in data["active"])
        mock_ai.assert_called_once()


class TestActions:

    def _first_active(self, client):
        data = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        return data["active"][0]

    def test_accept(self, client, mock_player):
        rec = self._first_active(client)
        resp = client.post(f"/api/players/{PLAYER_UID}/recommendations/{rec['id']}/accept", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "accepted"

    def test_complete_moves_to_history(self, client, mock_player):
        rec = self._first_active(client)
        client.post(f"/api/players/{PLAYER_UID}/recommendations/{rec['id']}/complete", headers=auth_headers())
        data = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        assert all(r["id"] != rec["id"] for r in data["active"])
        assert any(r["id"] == rec["id"] and r["status"] == "completed" for r in data["completed"])

    def test_refuse_returns_replacement_same_category(self, client, mock_player):
        rec = self._first_active(client)
        resp = client.post(f"/api/players/{PLAYER_UID}/recommendations/{rec['id']}/refuse", headers=auth_headers())
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["refused"] == rec["id"]
        assert body["replacement"]["category"] == rec["category"]
        assert body["replacement"]["text"] != rec["text"]
        assert body["replacement"]["status"] == "pending"

    def test_generate_creates_new_set(self, client, mock_player):
        first = client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers()).get_json()
        resp  = client.post(f"/api/players/{PLAYER_UID}/recommendations/generate", headers=auth_headers())
        assert resp.status_code == 200
        fresh = resp.get_json()
        assert len(fresh["active"]) >= 1
        old_ids = {r["id"] for r in first["active"]}
        new_ids = {r["id"] for r in fresh["active"]}
        assert old_ids.isdisjoint(new_ids)

    def test_action_requires_access(self, client, mock_player):
        resp = client.post(f"/api/players/{PLAYER2_UID}/recommendations/1/accept", headers=auth_headers())
        assert resp.status_code == 403
