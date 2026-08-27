import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    return app.test_client()


def test_health_endpoint_returns_success(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {
        "success": True,
        "message": "Service is healthy",
        "data": {"service": "enterprise-task-management-api"},
        "error": None,
    }
