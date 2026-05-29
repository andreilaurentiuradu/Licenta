from tests.conftest import auth_headers


class TestSubmitFeedback:

    def test_requires_auth(self, client):
        resp = client.post("/api/feedback/", json={"ratings": {"Overall": 5}})
        assert resp.status_code == 401

    def test_missing_ratings_rejected(self, client, mock_player):
        resp = client.post("/api/feedback/", json={"message": "good"}, headers=auth_headers())
        assert resp.status_code == 400
        assert "ratings" in resp.get_json()["error"]

    def test_empty_ratings_rejected(self, client, mock_player):
        resp = client.post("/api/feedback/", json={"ratings": {}}, headers=auth_headers())
        assert resp.status_code == 400

    def test_submit_success(self, client, mock_player):
        resp = client.post("/api/feedback/", json={
            "ratings": {"Overall experience": 5, "Performance": 4},
            "message": "Great platform",
        }, headers=auth_headers())
        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data

    def test_submit_persists_to_db(self, client, mock_player, app):
        client.post("/api/feedback/", json={
            "ratings": {"Overall": 5},
        }, headers=auth_headers())
        from models import Feedback
        with app.app_context():
            assert Feedback.query.count() == 1
            fb = Feedback.query.first()
            assert fb.user_id == "player-uid-1"
            assert fb.ratings == {"Overall": 5}


class TestListFeedback:

    def test_player_cannot_list(self, client, mock_player):
        resp = client.get("/api/feedback/", headers=auth_headers())
        assert resp.status_code == 403

    def test_admin_can_list_empty(self, client, mock_admin):
        resp = client.get("/api/feedback/", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_admin_sees_all_submissions(self, client, mock_player, mock_admin, app):
        # Submit two feedback entries
        mocker_patch = mock_player  # player token active for POSTs
        client.post("/api/feedback/", json={"ratings": {"Overall": 5}}, headers=auth_headers())
        client.post("/api/feedback/", json={"ratings": {"Overall": 3}}, headers=auth_headers())

        # Switch to admin for GET
        mock_admin  # admin token active
        resp = client.get("/api/feedback/", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2
