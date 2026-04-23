import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["KEYCLOAK_URL"] = "http://keycloak:8080"

import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app():
    app = create_app("development")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def mock_admin_token(mocker):
    """Mock Keycloak admin token retrieval."""
    return mocker.patch(
        "app.api.keycloak_auth._admin_token",
        return_value="mock-admin-token",
    )


@pytest.fixture
def mock_verify_token(mocker):
    """Replace Keycloak JWT verification with a stub returning chosen claims."""
    def _set(claims):
        return mocker.patch("app.api.keycloak_auth._verify_token", return_value=claims)
    return _set


def auth_headers(token="mock-user-token"):
    return {"Authorization": f"Bearer {token}"}


COACH_CLAIMS = {
    "sub":                "coach-sub-123",
    "preferred_username": "coach_user",
    "email":              "coach@sport.local",
    "realm_access":       {"roles": ["coach"]},
}

ADMIN_CLAIMS = {
    "sub":                "admin-sub-456",
    "preferred_username": "admin_user",
    "email":              "admin@sport.local",
    "realm_access":       {"roles": ["admin"]},
}

PLAYER_CLAIMS = {
    "sub":                "player-sub-789",
    "preferred_username": "player_user",
    "email":              "player@sport.local",
    "realm_access":       {"roles": ["player"]},
}
