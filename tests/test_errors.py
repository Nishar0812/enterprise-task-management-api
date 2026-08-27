import pytest

from app import create_app


@pytest.fixture
def app():
    application = create_app("testing")

    @application.route("/__boom")
    def boom():
        raise ValueError("should never reach the client")

    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_method_not_allowed_returns_json_envelope(client):
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.content_type == "application/json"
    body = response.get_json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_not_found_still_returns_dedicated_message(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "message": "Resource not found",
        "data": None,
        "error": {"code": "NOT_FOUND"},
    }


def test_unexpected_exception_returns_clean_json_500(client):
    response = client.get("/__boom")

    assert response.status_code == 500
    assert response.content_type == "application/json"
    assert response.get_json() == {
        "success": False,
        "message": "Internal server error",
        "data": None,
        "error": {"code": "INTERNAL_SERVER_ERROR"},
    }

    raw_body = response.get_data(as_text=True)
    assert "Traceback" not in raw_body
    assert "ValueError" not in raw_body
    assert "should never reach the client" not in raw_body
