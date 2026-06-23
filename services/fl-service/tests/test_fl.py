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

    def _seed_model(self, app, round_=1):
        from models import FLGlobalModel, db
        with app.app_context():
            db.session.add(FLGlobalModel(
                round=round_,
                coef_json=json.dumps(np.zeros((1, 12)).tolist()),
                intercept_json=json.dumps(np.zeros(1).tolist()),
                accuracy=0.83, recall=0.7, loss=0.5,
                n_samples_total=100, clubs_count=2,
            ))
            db.session.commit()

    def test_status_with_global_model(self, client, mock_coach, app):
        self._seed_model(app, round_=1)
        resp = client.get("/api/fl/status", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ready"] is True
        assert data["round"] == 1
        assert data["clubs_count"] == 2
        # model-quality metrics are admin-only — hidden from coaches
        assert data["is_admin"] is False
        assert "accuracy" not in data
        assert "recall" not in data
        assert "loss" not in data

    def test_metrics_visible_to_admin(self, client, mock_admin, app):
        self._seed_model(app, round_=1)
        data = client.get("/api/fl/status", headers=auth_headers()).get_json()
        assert data["is_admin"] is True
        assert data["accuracy"] == 0.83
        assert data["recall"] == 0.7
        assert data["loss"] == 0.5


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


class TestInternalRisk:

    def test_returns_risk_dict(self, client, mocker):
        mocker.patch(
            "fl.features.predict_injury_risk",
            return_value={"risk": "low", "probability": 0.12},
        )
        resp = client.get("/internal/risk/some-uid")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["risk"] == "low"
        assert data["probability"] == 0.12

    def test_falls_back_on_error(self, client, mocker):
        mocker.patch("fl.features.predict_injury_risk", side_effect=Exception("no model"))
        resp = client.get("/internal/risk/some-uid")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["risk"] == "low"
        assert data["probability"] == 0.0


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


class TestRiskRanking:

    def test_requires_auth(self, client):
        resp = client.get("/api/fl/risk")
        assert resp.status_code == 401

    def test_player_forbidden(self, client, mock_player):
        resp = client.get("/api/fl/risk", headers=auth_headers())
        assert resp.status_code == 403

    def test_coach_without_club_returns_empty(self, client, mocker):
        mocker.patch("auth._verify_token", return_value={
            "sub": "coach-no-club",
            "preferred_username": "coach_noclub",
            "realm_access": {"roles": ["coach"]},
        })
        mocker.patch("routes._fetch_user_club", return_value=None)
        resp = client.get("/api/fl/risk", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_sorted_by_probability(self, client, mock_coach, app, mocker):
        from models import PlayerProfile, db
        mocker.patch("routes._fetch_user_club", return_value="TestClub")

        with app.app_context():
            db.session.add(PlayerProfile(user_id="p1", username="player1", club="TestClub"))
            db.session.add(PlayerProfile(user_id="p2", username="player2", club="TestClub"))
            db.session.commit()

        mocker.patch("fl.features.predict_injury_risk", side_effect=[
            {"risk": "low",  "probability": 0.10},
            {"risk": "high", "probability": 0.90},
        ])

        resp = client.get("/api/fl/risk", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        assert data[0]["probability"] > data[1]["probability"]
        assert data[0]["risk"] == "high"

    def test_result_contains_required_fields(self, client, mock_coach, app, mocker):
        from models import PlayerProfile, db
        mocker.patch("routes._fetch_user_club", return_value="TestClub")

        with app.app_context():
            db.session.add(PlayerProfile(
                user_id="p1", username="player1",
                club="TestClub", position="Midfielder",
            ))
            db.session.commit()

        mocker.patch("fl.features.predict_injury_risk",
                     return_value={"risk": "medium", "probability": 0.45})

        resp = client.get("/api/fl/risk", headers=auth_headers())
        player = resp.get_json()[0]
        assert "user_id" in player
        assert "username" in player
        assert "risk" in player
        assert "probability" in player
        assert player["risk"] in ("low", "medium", "high")
