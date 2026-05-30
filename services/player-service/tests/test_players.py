from tests.conftest import auth_headers, PLAYER_UID, PLAYER2_UID


class TestBiometrics:

    def test_requires_auth(self, client):
        resp = client.get(f"/api/players/{PLAYER_UID}/biometrics")
        assert resp.status_code == 401

    def test_player_cannot_access_other_player(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER2_UID}/biometrics", headers=auth_headers())
        assert resp.status_code == 403

    def test_player_can_access_own_biometrics(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER_UID}/biometrics", headers=auth_headers())
        assert resp.status_code == 200

    def test_coach_can_access_any_player(self, client, mock_coach):
        resp = client.get(f"/api/players/{PLAYER_UID}/biometrics", headers=auth_headers())
        assert resp.status_code == 200

    def test_upsert_creates_profile(self, client, mock_player, app):
        resp = client.put(f"/api/players/{PLAYER_UID}/biometrics", json={
            "position": "Midfielder",
            "height_cm": 178.0,
            "weight_kg": 74.5,
            "birth_year": 1998,
        }, headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["position"] == "Midfielder"
        assert data["height_cm"] == 178.0

    def test_upsert_updates_existing(self, client, mock_player):
        client.put(f"/api/players/{PLAYER_UID}/biometrics",
                   json={"position": "Forward"}, headers=auth_headers())
        resp = client.put(f"/api/players/{PLAYER_UID}/biometrics",
                          json={"position": "Defender"}, headers=auth_headers())
        assert resp.get_json()["position"] == "Defender"


class TestTraining:

    def test_requires_auth(self, client):
        resp = client.post(f"/api/players/{PLAYER_UID}/training", json={})
        assert resp.status_code == 401

    def test_add_training_log(self, client, mock_player):
        resp = client.post(f"/api/players/{PLAYER_UID}/training", json={
            "date": "2024-03-01",
            "training_hours": 1.5,
            "matches_played": 0,
            "warmup_adherence": 1.0,
        }, headers=auth_headers())
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["training_hours"] == 1.5
        assert data["warmup_adherence"] == 1.0

    def test_get_training_returns_list(self, client, mock_player):
        client.post(f"/api/players/{PLAYER_UID}/training",
                    json={"date": "2024-03-01", "training_hours": 2.0},
                    headers=auth_headers())
        resp = client.get(f"/api/players/{PLAYER_UID}/training", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    def test_delete_training(self, client, mock_player):
        post = client.post(f"/api/players/{PLAYER_UID}/training",
                           json={"date": "2024-03-02", "training_hours": 1.0},
                           headers=auth_headers())
        lid = post.get_json()["id"]
        resp = client.delete(f"/api/players/{PLAYER_UID}/training/{lid}",
                             headers=auth_headers())
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] == lid

    def test_missing_date_rejected(self, client, mock_player):
        resp = client.post(f"/api/players/{PLAYER_UID}/training",
                           json={"training_hours": 2.0}, headers=auth_headers())
        assert resp.status_code == 400


class TestPhysical:

    def test_add_physical_assessment(self, client, mock_player):
        resp = client.post(f"/api/players/{PLAYER_UID}/physical", json={
            "date": "2024-03-01",
            "knee_strength_score": 80.0,
            "hamstring_flexibility": 75.0,
            "reaction_time_ms": 240.0,
            "balance_test_score": 85.0,
            "sprint_speed_10m_s": 6.1,
            "agility_score": 79.0,
        }, headers=auth_headers())
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["knee_strength_score"] == 80.0

    def test_get_physical_returns_list(self, client, mock_player):
        client.post(f"/api/players/{PLAYER_UID}/physical",
                    json={"date": "2024-03-01", "knee_strength_score": 77.0},
                    headers=auth_headers())
        resp = client.get(f"/api/players/{PLAYER_UID}/physical", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1


class TestWellness:

    def test_add_wellness_log(self, client, mock_player):
        resp = client.post(f"/api/players/{PLAYER_UID}/wellness", json={
            "date": "2024-03-01",
            "sleep_hours": 7.5,
            "stress_level": 4,
            "mood_score": 7,
            "calories": 3000,
            "protein_g": 160,
            "carbs_g": 350,
            "fat_g": 80,
            "hydration_ml": 2800,
        }, headers=auth_headers())
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["sleep_hours"] == 7.5
        # nutrition_score should be computed automatically (> 50 base)
        assert data["nutrition_score"] is not None
        assert data["nutrition_score"] > 50

    def test_get_wellness_returns_list(self, client, mock_player):
        client.post(f"/api/players/{PLAYER_UID}/wellness",
                    json={"date": "2024-03-01", "sleep_hours": 8.0},
                    headers=auth_headers())
        resp = client.get(f"/api/players/{PLAYER_UID}/wellness", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    def test_delete_wellness(self, client, mock_player):
        post = client.post(f"/api/players/{PLAYER_UID}/wellness",
                           json={"date": "2024-03-03", "sleep_hours": 6.0},
                           headers=auth_headers())
        wid = post.get_json()["id"]
        resp = client.delete(f"/api/players/{PLAYER_UID}/wellness/{wid}",
                             headers=auth_headers())
        assert resp.status_code == 200


class TestInjuries:

    def test_add_injury(self, client, mock_player):
        resp = client.post(f"/api/players/{PLAYER_UID}/injuries", json={
            "date": "2024-01-15",
            "injury_type": "Hamstring strain",
            "injury_severity": "moderate",
            "rehabilitation_weeks": 4,
        }, headers=auth_headers())
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["injury_type"] == "Hamstring strain"

    def test_get_injuries_returns_list(self, client, mock_player):
        client.post(f"/api/players/{PLAYER_UID}/injuries",
                    json={"date": "2024-01-15", "injury_type": "Knee sprain",
                          "injury_severity": "minor"},
                    headers=auth_headers())
        resp = client.get(f"/api/players/{PLAYER_UID}/injuries", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1

    def test_player_cannot_access_other_injuries(self, client, mock_player):
        resp = client.get(f"/api/players/{PLAYER2_UID}/injuries", headers=auth_headers())
        assert resp.status_code == 403


class TestListPlayers:

    def test_player_cannot_list(self, client, mock_player):
        resp = client.get("/api/players/", headers=auth_headers())
        assert resp.status_code == 403

    def test_coach_without_club_sees_nobody(self, client, mock_coach_no_club, mocker):
        mocker.patch("routes._fetch_user_club", return_value=None)
        mocker.patch("routes._admin_token", return_value="fake-token")
        mocker.patch("routes.requests.get", return_value=type("R", (), {
            "status_code": 200,
            "json": lambda self: [
                {"id": "uid-1", "username": "player1", "email": "p1@test.com",
                 "attributes": {"club": ["OtherClub"]}},
            ],
        })())
        resp = client.get("/api/players/", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_coach_sees_only_own_club(self, client, mock_coach, mocker):
        mocker.patch("routes._fetch_user_club", return_value="TestClub")
        mocker.patch("routes._admin_token", return_value="fake-token")
        mocker.patch("routes.requests.get", return_value=type("R", (), {
            "status_code": 200,
            "json": lambda self: [
                {"id": "uid-1", "username": "player1", "email": "p1@test.com",
                 "attributes": {"club": ["TestClub"]}},
                {"id": "uid-2", "username": "player2", "email": "p2@test.com",
                 "attributes": {"club": ["OtherClub"]}},
            ],
        })())
        resp = client.get("/api/players/", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["username"] == "player1"
