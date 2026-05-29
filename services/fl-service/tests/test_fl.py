import json
import numpy as np
from tests.conftest import auth_headers


class TestFlStatus:

    def test_requires_auth(self, client):
        resp = client.get("/api/fl/status")
        assert resp.status_code == 401

    def test_player_forbidden(self, client, mock_player):
        resp = client.get("/api/fl/status", headers=auth_headers())
        assert resp.status_code == 403

    def test_no_model_returns_not_ready(self, client, mock_coach):
        resp = client.get("/api/fl/status", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ready"] is False

    def test_status_with_global_model(self, client, mock_coach, app):
        from models import FLGlobalModel, db
        coef      = np.zeros((1, 12))
        intercept = np.zeros(1)
        with app.app_context():
            db.session.add(FLGlobalModel(
                round=1,
                coef_json=json.dumps(coef.tolist()),
                intercept_json=json.dumps(intercept.tolist()),
                accuracy=0.83,
                n_samples_total=100,
                clubs_count=2,
            ))
            db.session.commit()

        resp = client.get("/api/fl/status", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ready"] is True
        assert data["round"] == 1
        assert data["accuracy"] == 0.83
        assert data["clubs_count"] == 2


class TestInternalTrigger:

    def test_missing_club_returns_400(self, client):
        resp = client.post("/internal/trigger", json={})
        assert resp.status_code == 400

    def test_empty_club_returns_400(self, client):
        resp = client.post("/internal/trigger", json={"club": ""})
        assert resp.status_code == 400

    def test_valid_club_schedules_update(self, client, mocker):
        mocker.patch("fl.pipeline.trigger_fl_update", return_value=None)
        resp = client.post("/internal/trigger", json={"club": "TestClub"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["scheduled"] is True
        assert data["club"] == "TestClub"


class TestFlTrain:

    def test_requires_auth(self, client):
        resp = client.post("/api/fl/train")
        assert resp.status_code == 401

    def test_player_forbidden(self, client, mock_player):
        resp = client.post("/api/fl/train", headers=auth_headers())
        assert resp.status_code == 403

    def test_coach_with_no_players_returns_warning(self, client, mock_coach, mocker):
        mocker.patch("routes._fetch_user_club", return_value="EmptyClub")
        resp = client.post("/api/fl/train", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["trained"] is False
        assert "warning" in data or "players" in data["message"].lower()

    def test_coach_triggers_fl_for_own_club(self, client, mock_coach, app, mocker):
        from models import PlayerProfile, db
        mocker.patch("fl.pipeline._do_club_update", return_value=None)
        mocker.patch("routes._fetch_user_club", return_value="TestClub")

        with app.app_context():
            db.session.add(PlayerProfile(
                user_id="p1", username="player1", club="TestClub",
            ))
            db.session.commit()

        resp = client.post("/api/fl/train", headers=auth_headers())
        assert resp.status_code == 200
