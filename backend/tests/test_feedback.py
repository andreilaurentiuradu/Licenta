from app.extensions import db
from app.models import Feedback
from tests.conftest import COACH_CLAIMS, ADMIN_CLAIMS, PLAYER_CLAIMS, auth_headers


class TestSubmitFeedback:

    def test_requires_auth(self, client):
        resp = client.post("/api/feedback/", json={
            "ratings": {"Overall experience": 5},
            "message": "great",
        })
        assert resp.status_code == 401

    def test_missing_ratings_rejected(self, client, mock_verify_token):
        mock_verify_token(COACH_CLAIMS)
        resp = client.post("/api/feedback/", json={"message": "hi"}, headers=auth_headers())
        assert resp.status_code == 400

    def test_empty_ratings_rejected(self, client, mock_verify_token):
        mock_verify_token(COACH_CLAIMS)
        resp = client.post(
            "/api/feedback/",
            json={"ratings": {}, "message": ""},
            headers=auth_headers(),
        )
        assert resp.status_code == 400

    def test_ratings_must_be_object(self, client, mock_verify_token):
        mock_verify_token(COACH_CLAIMS)
        resp = client.post(
            "/api/feedback/",
            json={"ratings": [1, 2, 3], "message": ""},
            headers=auth_headers(),
        )
        assert resp.status_code == 400

    def test_coach_can_submit(self, client, app, mock_verify_token):
        mock_verify_token(COACH_CLAIMS)
        payload = {
            "ratings": {"Overall experience": 4, "UI & Design": 5, "Performance": 4, "Ease of use": 5},
            "message": "Great job!",
        }
        resp = client.post("/api/feedback/", json=payload, headers=auth_headers())
        assert resp.status_code == 201
        assert "id" in resp.get_json()

        with app.app_context():
            items = Feedback.query.all()
            assert len(items) == 1
            fb = items[0]
            assert fb.user_id  == "coach-sub-123"
            assert fb.username == "coach_user"
            assert fb.ratings["UI & Design"] == 5
            assert fb.message == "Great job!"

    def test_player_can_submit(self, client, app, mock_verify_token):
        mock_verify_token(PLAYER_CLAIMS)
        resp = client.post(
            "/api/feedback/",
            json={"ratings": {"Overall experience": 5}, "message": ""},
            headers=auth_headers(),
        )
        assert resp.status_code == 201

        with app.app_context():
            fb = Feedback.query.first()
            assert fb.user_id  == "player-sub-789"
            assert fb.username == "player_user"

    def test_message_is_optional(self, client, mock_verify_token):
        mock_verify_token(COACH_CLAIMS)
        resp = client.post(
            "/api/feedback/",
            json={"ratings": {"Overall experience": 3}},
            headers=auth_headers(),
        )
        assert resp.status_code == 201


class TestListFeedback:

    def test_requires_auth(self, client):
        resp = client.get("/api/feedback/")
        assert resp.status_code == 401

    def test_non_admin_rejected(self, client, mock_verify_token):
        mock_verify_token(COACH_CLAIMS)
        resp = client.get("/api/feedback/", headers=auth_headers())
        assert resp.status_code == 403

    def test_admin_sees_all_feedback(self, client, app, mock_verify_token):
        with app.app_context():
            db.session.add(Feedback(
                user_id="u1", username="alice",
                ratings={"Overall experience": 5},
                message="nice",
            ))
            db.session.add(Feedback(
                user_id="u2", username="bob",
                ratings={"Overall experience": 3},
                message="meh",
            ))
            db.session.commit()

        mock_verify_token(ADMIN_CLAIMS)
        resp = client.get("/api/feedback/", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        usernames = {item["username"] for item in data}
        assert usernames == {"alice", "bob"}

    def test_empty_list_for_admin(self, client, mock_verify_token):
        mock_verify_token(ADMIN_CLAIMS)
        resp = client.get("/api/feedback/", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.get_json() == []


class TestFeedbackModel:

    def test_to_dict_contains_expected_fields(self, app):
        with app.app_context():
            fb = Feedback(
                user_id="u1", username="alice",
                ratings={"Overall experience": 5},
                message="nice",
            )
            db.session.add(fb)
            db.session.commit()

            d = fb.to_dict()
            assert d["username"] == "alice"
            assert d["ratings"]["Overall experience"] == 5
            assert d["message"]  == "nice"
            assert "created_at" in d
            assert "id"         in d
