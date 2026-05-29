import os
import sys
import pathlib

os.environ.setdefault("KEYCLOAK_URL", "http://localhost")
os.environ.setdefault("KEYCLOAK_REALM", "test")

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from app import app as _app

ADMIN_CLAIMS = {
    "sub": "admin-uid-1",
    "preferred_username": "admin1",
    "email": "admin1@test.com",
    "realm_access": {"roles": ["admin"]},
}

PLAYER_CLAIMS = {
    "sub": "player-uid-1",
    "preferred_username": "player1",
    "email": "player1@test.com",
    "realm_access": {"roles": ["player"]},
}


def auth_headers():
    return {"Authorization": "Bearer fake.token.value"}


@pytest.fixture
def app():
    _app.config["TESTING"] = True
    return _app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_admin(mocker):
    return mocker.patch("auth._verify_token", return_value=ADMIN_CLAIMS)


@pytest.fixture
def mock_player(mocker):
    return mocker.patch("auth._verify_token", return_value=PLAYER_CLAIMS)
