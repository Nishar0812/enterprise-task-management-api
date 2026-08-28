import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _register_and_login(client, email="nishar@example.com", password="StrongPassword123!"):
    client.post(
        "/api/v1/auth/register",
        json={"name": "Nishar", "email": email, "password": password},
    )
    login_response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return login_response.get_json()["data"]["access_token"]


def test_get_me_without_jwt_returns_standard_error_envelope(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"] is not None
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_get_me_with_invalid_jwt_returns_standard_error_envelope(client):
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_get_me_with_valid_jwt_returns_current_user(client):
    access_token = _register_and_login(client)

    response = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "User retrieved successfully"
    assert body["data"]["email"] == "nishar@example.com"
    assert body["data"]["name"] == "Nishar"
    assert body["data"]["role"] == "member"


def test_get_me_response_never_exposes_password_hash(client):
    access_token = _register_and_login(client)

    response = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    body = response.get_json()

    assert "password" not in body["data"]
    assert "password_hash" not in body["data"]
    assert "password_hash" not in response.get_data(as_text=True)
