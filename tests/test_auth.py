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


def _register_payload(**overrides):
    payload = {
        "name": "Nishar",
        "email": "nishar@example.com",
        "password": "StrongPassword123!",
    }
    payload.update(overrides)
    return payload


def _register(client, **overrides):
    return client.post("/api/v1/auth/register", json=_register_payload(**overrides))


def _login(client, email="nishar@example.com", password="StrongPassword123!"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_register_success(client):
    response = _register(client)

    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "User registered successfully"
    assert body["error"] is None
    assert body["data"]["name"] == "Nishar"
    assert body["data"]["email"] == "nishar@example.com"
    assert body["data"]["role"] == "member"
    assert isinstance(body["data"]["id"], int)


def test_register_normalizes_email_case_and_whitespace(client):
    response = _register(client, email="  Nishar@Example.com  ")

    assert response.status_code == 201
    assert response.get_json()["data"]["email"] == "nishar@example.com"


def test_register_duplicate_email_returns_4xx(client):
    _register(client)
    response = _register(client, name="Someone Else")

    assert 400 <= response.status_code < 500
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_duplicate_email_is_case_insensitive(client):
    _register(client, email="nishar@example.com")
    response = _register(client, email="NISHAR@EXAMPLE.COM")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"email": "not-a-valid-email"},
        {"password": "short"},
    ],
)
def test_register_invalid_data_returns_400(client, overrides):
    response = _register(client, **overrides)

    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_register_missing_fields_returns_400(client):
    response = client.post("/api/v1/auth/register", json={})

    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_register_malformed_json_returns_400(client):
    response = client.post(
        "/api/v1/auth/register",
        data="not json",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_register_response_does_not_expose_password(client):
    response = _register(client)
    body = response.get_json()

    assert "password" not in body["data"]
    assert "password_hash" not in body["data"]
    assert "password" not in response.get_data(as_text=True)
    assert "password_hash" not in response.get_data(as_text=True)


def test_login_success(client):
    _register(client)
    response = _login(client)

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "Login successful"
    assert isinstance(body["data"]["access_token"], str)
    assert body["data"]["user"]["email"] == "nishar@example.com"
    assert body["data"]["user"]["role"] == "member"


def test_login_response_does_not_expose_password(client):
    _register(client)
    response = _login(client)
    body = response.get_json()

    assert "password" not in body["data"]["user"]
    assert "password_hash" not in body["data"]["user"]
    assert "password_hash" not in response.get_data(as_text=True)


def test_login_wrong_password_returns_generic_error(client):
    _register(client)
    response = _login(client, password="WrongPassword123!")

    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert "access_token" not in (body["data"] or {})


def test_login_unknown_email_returns_generic_error(client):
    response = _login(client, email="unknown@example.com")

    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_wrong_password_and_unknown_email_return_identical_message(client):
    _register(client)

    wrong_password = _login(client, password="WrongPassword123!")
    unknown_email = _login(client, email="unknown@example.com")

    assert wrong_password.status_code == unknown_email.status_code
    assert wrong_password.get_json()["message"] == unknown_email.get_json()["message"]
    assert wrong_password.get_json()["error"] == unknown_email.get_json()["error"]
