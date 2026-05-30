import pytest
from tests.conftest import auth_headers, PLAYER_UID, PLAYER2_UID

FL_RISK_LOW  = {"risk": "low",  "probability": 0.04}
FL_RISK_HIGH = {"risk": "high", "probability": 0.97}


@pytest.fixture(autouse=True)
def mock_fl_risk(mocker):
    """Silence the HTTP call to fl-service in every test."""
    return mocker.patch("routes._fetch_fl_risk", return_value=FL_RISK_LOW)


class TestRecommendations:

    def test_requires_auth(self, client):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations")
        assert resp.status_code == 401

    def test_player_cannot_access_other_player(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER2_UID}/recommendations",
                          headers=auth_headers())
        assert resp.status_code == 403

    def test_player_can_access_own(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        assert resp.status_code == 200

    def test_coach_can_access_any_player(self, client, mock_coach):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        assert resp.status_code == 200

    def test_no_api_key_returns_defaults(self, client, mock_player, app):
        app.config["GROQ_API_KEY"] = ""
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ai_generated"] is False
        assert len(data["recommendations"]) >= 1
        assert "last_updated" in data

    def test_response_has_required_fields(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        data = resp.get_json()
        assert "injury_risk" in data
        assert "fl_probability" in data
        assert "recommendations" in data
        assert "last_updated" in data
        assert "ai_generated" in data

    def test_injury_risk_comes_from_fl_model(self, client, mock_player, mocker):
        """injury_risk must always reflect the FL model, not the LLM's guess."""
        mocker.patch("routes._fetch_fl_risk", return_value=FL_RISK_HIGH)
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        data = resp.get_json()
        assert data["injury_risk"] == "high"
        assert data["fl_probability"] == 0.97

    def test_injury_risk_is_valid_value(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        assert resp.get_json()["injury_risk"] in ("low", "medium", "high")

    def test_fl_probability_is_float(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        prob = resp.get_json()["fl_probability"]
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_recommendation_structure(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        recs = resp.get_json()["recommendations"]
        assert len(recs) >= 1
        for r in recs:
            assert "category" in r
            assert "priority" in r
            assert "text" in r
            assert r["priority"] in ("high", "medium", "low")

    def test_groq_used_when_key_present(self, client, mock_player, app, mocker):
        app.config["GROQ_API_KEY"] = "test-key"
        mocker.patch("routes._fetch_fl_risk", return_value=FL_RISK_HIGH)
        mock_ai = mocker.patch("routes._call_openai", return_value={
            "recommendations": [{
                "category": "Injury Prevention",
                "priority": "high",
                "text": "Test recommendation.",
            }],
        })
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ai_generated"] is True
        # injury_risk comes from FL, not from LLM response
        assert data["injury_risk"] == "high"
        assert data["fl_probability"] == 0.97
        mock_ai.assert_called_once()

    def test_fl_risk_fetched_for_every_request(self, client, mock_player, mocker):
        mock_fl = mocker.patch("routes._fetch_fl_risk", return_value=FL_RISK_LOW)
        client.get(f"/api/players/{PLAYER_UID}/recommendations", headers=auth_headers())
        mock_fl.assert_called_once_with(PLAYER_UID)
