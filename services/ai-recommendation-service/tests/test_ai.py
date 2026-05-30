from tests.conftest import auth_headers, PLAYER_UID, PLAYER2_UID


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
        assert "recommendations" in data
        assert "last_updated" in data
        assert "ai_generated" in data

    def test_injury_risk_is_valid_value(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER_UID}/recommendations",
                          headers=auth_headers())
        risk = resp.get_json()["injury_risk"]
        assert risk in ("low", "medium", "high")

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

    def test_groq_call_used_when_key_present(self, client, mock_player, app, mocker):
        app.config["GROQ_API_KEY"] = "test-key"
        mock_ai = mocker.patch("routes._call_openai", return_value={
            "injury_risk": "medium",
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
        assert data["injury_risk"] == "medium"
        mock_ai.assert_called_once()
