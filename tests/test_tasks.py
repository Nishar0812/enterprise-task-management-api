import pytest

from app import create_app
from app.extensions import db
from app.models import Project, Task, User


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _register_and_login(client, email, password="StrongPassword123!", name="Test User"):
    client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return response.get_json()["data"]["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_project(client, token, name="Project A"):
    return client.post(
        "/api/v1/projects", json={"name": name}, headers=_auth_header(token)
    )


def _create_task(client, token, project_id, **overrides):
    payload = {"title": "Task A"}
    payload.update(overrides)
    return client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json=payload,
        headers=_auth_header(token),
    )


def test_create_task_success(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = _create_task(
        client,
        token,
        project_id,
        title="Ship API",
        description="Complete Milestone 4",
        status="in_progress",
        priority="high",
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "Task created successfully"
    assert body["data"]["title"] == "Ship API"
    assert body["data"]["description"] == "Complete Milestone 4"
    assert body["data"]["status"] == "in_progress"
    assert body["data"]["priority"] == "high"
    assert body["data"]["project_id"] == project_id


def test_create_task_uses_defaults_and_normalizes_title(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = _create_task(client, token, project_id, title="  Trim me  ")

    data = response.get_json()["data"]
    assert data["title"] == "Trim me"
    assert data["description"] is None
    assert data["status"] == "pending"
    assert data["priority"] == "medium"
    assert data["assigned_to"] is None


def test_create_task_without_jwt_returns_401(client):
    response = client.post("/api/v1/projects/1/tasks", json={"title": "Task"})

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_create_task_in_another_users_project_returns_403(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]

    response = _create_task(client, other_token, project_id)

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_create_task_for_nonexistent_project_returns_404(client):
    token = _register_and_login(client, "owner@example.com")

    response = _create_task(client, token, 9999)

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "   "},
        {"title": "Task", "status": "archived"},
        {"title": "Task", "priority": "urgent"},
        {"title": "Task", "assigned_to": "1"},
    ],
)
def test_create_task_invalid_payload_returns_validation_error(client, payload):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json=payload,
        headers=_auth_header(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_task_with_malformed_json_returns_400(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        data="not json",
        content_type="application/json",
        headers=_auth_header(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_JSON"


def test_create_task_with_nonexistent_assignee_returns_404(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = _create_task(client, token, project_id, assigned_to=9999)

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_list_own_project_tasks_successfully(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    _create_task(client, token, project_id, title="First")
    _create_task(client, token, project_id, title="Second")

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks", headers=_auth_header(token)
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Tasks retrieved successfully"
    assert {task["title"] for task in response.get_json()["data"]} == {
        "First",
        "Second",
    }


def test_list_tasks_only_for_requested_project(client):
    token = _register_and_login(client, "owner@example.com")
    first_id = _create_project(client, token, "First Project").get_json()["data"]["id"]
    second_id = _create_project(client, token, "Second Project").get_json()["data"]["id"]
    _create_task(client, token, first_id, title="First Task")
    _create_task(client, token, second_id, title="Second Task")

    response = client.get(
        f"/api/v1/projects/{first_id}/tasks", headers=_auth_header(token)
    )

    tasks = response.get_json()["data"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "First Task"
    assert tasks[0]["project_id"] == first_id


def test_list_another_users_project_tasks_returns_403(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}/tasks", headers=_auth_header(other_token)
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_get_own_task_successfully(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    task_id = _create_task(client, token, project_id).get_json()["data"]["id"]

    response = client.get(f"/api/v1/tasks/{task_id}", headers=_auth_header(token))

    assert response.status_code == 200
    assert response.get_json()["message"] == "Task retrieved successfully"
    assert response.get_json()["data"]["id"] == task_id


def test_get_another_users_task_returns_403(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]
    task_id = _create_task(client, owner_token, project_id).get_json()["data"]["id"]

    response = client.get(
        f"/api/v1/tasks/{task_id}", headers=_auth_header(other_token)
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_get_nonexistent_task_returns_404(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.get("/api/v1/tasks/9999", headers=_auth_header(token))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_update_own_task_successfully(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    task_id = _create_task(client, token, project_id).get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Updated",
            "description": "Changed",
            "status": "completed",
            "priority": "low",
        },
        headers=_auth_header(token),
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["title"] == "Updated"
    assert data["description"] == "Changed"
    assert data["status"] == "completed"
    assert data["priority"] == "low"
    assert data["project_id"] == project_id


def test_update_task_can_assign_and_unassign_user(client):
    token = _register_and_login(client, "owner@example.com")
    _register_and_login(client, "assignee@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    task_id = _create_task(client, token, project_id).get_json()["data"]["id"]

    with client.application.app_context():
        assignee_id = User.query.filter_by(email="assignee@example.com").one().id

    assigned = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assigned_to": assignee_id},
        headers=_auth_header(token),
    )
    unassigned = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assigned_to": None},
        headers=_auth_header(token),
    )

    assert assigned.status_code == 200
    assert assigned.get_json()["data"]["assigned_to"] == assignee_id
    assert unassigned.status_code == 200
    assert unassigned.get_json()["data"]["assigned_to"] is None


def test_assignee_does_not_gain_task_access(client):
    owner_token = _register_and_login(client, "owner@example.com")
    assignee_token = _register_and_login(client, "assignee@example.com")
    with client.application.app_context():
        assignee_id = User.query.filter_by(email="assignee@example.com").one().id
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]
    task_id = _create_task(
        client, owner_token, project_id, assigned_to=assignee_id
    ).get_json()["data"]["id"]

    response = client.get(
        f"/api/v1/tasks/{task_id}", headers=_auth_header(assignee_token)
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_update_another_users_task_returns_403_and_leaves_task_unchanged(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]
    task_id = _create_task(
        client, owner_token, project_id, title="Original"
    ).get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Hijacked"},
        headers=_auth_header(other_token),
    )

    assert response.status_code == 403
    check = client.get(
        f"/api/v1/tasks/{task_id}", headers=_auth_header(owner_token)
    )
    assert check.get_json()["data"]["title"] == "Original"


@pytest.mark.parametrize(
    "payload",
    [{}, {"title": "   "}, {"status": "archived"}, {"priority": "urgent"}],
)
def test_update_task_invalid_payload_returns_validation_error(client, payload):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    task_id = _create_task(client, token, project_id).get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/tasks/{task_id}", json=payload, headers=_auth_header(token)
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_own_task_successfully_without_deleting_project(app, client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    task_id = _create_task(client, token, project_id).get_json()["data"]["id"]

    response = client.delete(f"/api/v1/tasks/{task_id}", headers=_auth_header(token))

    assert response.status_code == 200
    assert response.get_json()["message"] == "Task deleted successfully"
    assert response.get_json()["data"] is None
    with app.app_context():
        assert db.session.get(Task, task_id) is None
        assert db.session.get(Project, project_id) is not None


def test_delete_another_users_task_returns_403_and_task_remains(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]
    task_id = _create_task(client, owner_token, project_id).get_json()["data"]["id"]

    response = client.delete(
        f"/api/v1/tasks/{task_id}", headers=_auth_header(other_token)
    )

    assert response.status_code == 403
    check = client.get(
        f"/api/v1/tasks/{task_id}", headers=_auth_header(owner_token)
    )
    assert check.status_code == 200


def test_task_endpoints_require_jwt(client):
    assert client.get("/api/v1/projects/1/tasks").status_code == 401
    assert client.get("/api/v1/tasks/1").status_code == 401
    assert client.patch("/api/v1/tasks/1", json={"title": "X"}).status_code == 401
    assert client.delete("/api/v1/tasks/1").status_code == 401


def test_admin_role_does_not_bypass_task_ownership(app, client):
    owner_token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]
    task_id = _create_task(client, owner_token, project_id).get_json()["data"]["id"]

    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("StrongPassword123!")
        db.session.add(admin)
        db.session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "StrongPassword123!"},
    )
    admin_token = login.get_json()["data"]["access_token"]

    assert _create_task(client, admin_token, project_id).status_code == 403
    assert client.get(
        f"/api/v1/projects/{project_id}/tasks", headers=_auth_header(admin_token)
    ).status_code == 403
    assert client.get(
        f"/api/v1/tasks/{task_id}", headers=_auth_header(admin_token)
    ).status_code == 403
