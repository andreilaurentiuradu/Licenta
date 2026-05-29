import os
import sys
import pathlib

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("KEYCLOAK_URL", "http://localhost")
os.environ.setdefault("KEYCLOAK_REALM", "test")

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from sqlalchemy.pool import StaticPool
from app import app as _app
from models import db as _db

PLAYER_UID  = "player-uid-1"
PLAYER2_UID = "player-uid-2"

PLAYER_CLAIMS = {
    "sub": PLAYER_UID,
    "preferred_username": "player1",
    "email": "player1@test.com",
    "realm_access": {"roles": ["player"]},
}

COACH_CLAIMS = {
    "sub": "coach-uid-1",
    "preferred_username": "coach1",
    "email": "coach1@test.com",
    "realm_access": {"roles": ["coach"]},
    "club": "TestClub",
}


def auth_headers():
    return {"Authorization": "Bearer fake.token.value"}


@pytest.fixture
def app():
    _app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
        "GROQ_API_KEY": "",
    })
    with _app.app_context():
        _db.create_all()
        yield _app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_player(mocker):
    return mocker.patch("auth._verify_token", return_value=PLAYER_CLAIMS)


@pytest.fixture
def mock_coach(mocker):
    return mocker.patch("auth._verify_token", return_value=COACH_CLAIMS)
