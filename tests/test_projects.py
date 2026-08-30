import pytest

from app import create_app
from app.extensions import db
from app.models import Task, User


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
    login_response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return login_response.get_json()["data"]["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_admin_and_login(app, client, email="admin@example.com", password="StrongPassword123!"):
    with app.app_context():
        admin = User(name="Admin", email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

    login_response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return login_response.get_json()["data"]["access_token"]


def _create_project(client, token, name="Project A", description="Desc A"):
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    return client.post(
        "/api/v1/projects", json=payload, headers=_auth_header(token)
    )


# ---- create ----------------------------------------------------------


def test_create_project_success(client):
    token = _register_and_login(client, "owner@example.com")

    response = _create_project(client, token, name="My Project", description="Details")

    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "Project created successfully"
    assert body["data"]["name"] == "My Project"
    assert body["data"]["description"] == "Details"
    assert isinstance(body["data"]["id"], int)


def test_create_project_without_description_defaults_to_null(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/v1/projects", json={"name": "No Desc"}, headers=_auth_header(token)
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["description"] is None


def test_create_project_sets_owner_id_to_current_user(client):
    token = _register_and_login(client, "owner@example.com")
    me = client.get("/api/v1/users/me", headers=_auth_header(token)).get_json()

    response = _create_project(client, token)

    assert response.get_json()["data"]["owner_id"] == me["data"]["id"]


def test_create_project_without_jwt_returns_401(client):
    response = client.post("/api/v1/projects", json={"name": "X"})

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_create_project_missing_name_returns_400(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.post("/api/v1/projects", json={}, headers=_auth_header(token))

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_project_blank_name_returns_400(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/v1/projects", json={"name": "   "}, headers=_auth_header(token)
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_project_malformed_json_returns_400(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/v1/projects",
        data="not json",
        content_type="application/json",
        headers=_auth_header(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_JSON"


# ---- list -------------------------------------------------------------


def test_list_projects_returns_only_own_projects(client):
    token_a = _register_and_login(client, "a@example.com")
    token_b = _register_and_login(client, "b@example.com")
    _create_project(client, token_a, name="A1")
    _create_project(client, token_a, name="A2")
    _create_project(client, token_b, name="B1")

    response = client.get("/api/v1/projects", headers=_auth_header(token_a))

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Projects retrieved successfully"
    names = {p["name"] for p in body["data"]}
    assert names == {"A1", "A2"}


def test_list_projects_empty_returns_empty_list(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.get("/api/v1/projects", headers=_auth_header(token))

    assert response.status_code == 200
    assert response.get_json()["data"] == []


def test_list_projects_without_jwt_returns_401(client):
    response = client.get("/api/v1/projects")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


# ---- get by id ----------------------------------------------------------


def test_get_project_success(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = client.get(f"/api/v1/projects/{project_id}", headers=_auth_header(token))

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Project retrieved successfully"
    assert body["data"]["id"] == project_id


def test_get_project_without_jwt_returns_401(client):
    response = client.get("/api/v1/projects/1")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_get_project_not_found_returns_404(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.get("/api/v1/projects/9999", headers=_auth_header(token))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_get_project_owned_by_another_user_returns_403(client):
    token_a = _register_and_login(client, "a@example.com")
    token_b = _register_and_login(client, "b@example.com")
    project_id = _create_project(client, token_a).get_json()["data"]["id"]

    response = client.get(f"/api/v1/projects/{project_id}", headers=_auth_header(token_b))

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


# ---- update -------------------------------------------------------------


def test_update_project_name_and_description(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Renamed", "description": "New desc"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Project updated successfully"
    assert body["data"]["name"] == "Renamed"
    assert body["data"]["description"] == "New desc"


def test_update_project_name_only_leaves_description_untouched(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token, description="Original").get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Renamed"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["name"] == "Renamed"
    assert body["data"]["description"] == "Original"


def test_update_project_description_only_leaves_name_untouched(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token, name="Keep Me").get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"description": "Updated desc"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["name"] == "Keep Me"
    assert body["data"]["description"] == "Updated desc"


def test_update_project_empty_body_returns_400(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/projects/{project_id}", json={}, headers=_auth_header(token)
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_project_blank_name_returns_400(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "   "},
        headers=_auth_header(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_project_without_jwt_returns_401(client):
    response = client.patch("/api/v1/projects/1", json={"name": "X"})

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_update_project_not_found_returns_404(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.patch(
        "/api/v1/projects/9999", json={"name": "X"}, headers=_auth_header(token)
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_update_project_owned_by_another_user_returns_403_and_leaves_unchanged(client):
    token_a = _register_and_login(client, "a@example.com")
    token_b = _register_and_login(client, "b@example.com")
    project_id = _create_project(client, token_a, name="Original").get_json()["data"]["id"]

    response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Hijacked"},
        headers=_auth_header(token_b),
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"

    check = client.get(f"/api/v1/projects/{project_id}", headers=_auth_header(token_a))
    assert check.get_json()["data"]["name"] == "Original"


# ---- delete -------------------------------------------------------------


def test_delete_project_success(client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response = client.delete(f"/api/v1/projects/{project_id}", headers=_auth_header(token))

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Project deleted successfully"
    assert body["data"] is None

    follow_up = client.get(f"/api/v1/projects/{project_id}", headers=_auth_header(token))
    assert follow_up.status_code == 404


def test_delete_project_without_jwt_returns_401(client):
    response = client.delete("/api/v1/projects/1")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_delete_project_not_found_returns_404(client):
    token = _register_and_login(client, "owner@example.com")

    response = client.delete("/api/v1/projects/9999", headers=_auth_header(token))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_delete_project_owned_by_another_user_returns_403_and_project_still_exists(client):
    token_a = _register_and_login(client, "a@example.com")
    token_b = _register_and_login(client, "b@example.com")
    project_id = _create_project(client, token_a).get_json()["data"]["id"]

    response = client.delete(f"/api/v1/projects/{project_id}", headers=_auth_header(token_b))

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"

    check = client.get(f"/api/v1/projects/{project_id}", headers=_auth_header(token_a))
    assert check.status_code == 200


def test_delete_project_also_deletes_associated_tasks(app, client):
    token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    with app.app_context():
        task_a = Task(title="Task A", project_id=project_id)
        task_b = Task(title="Task B", project_id=project_id)
        db.session.add_all([task_a, task_b])
        db.session.commit()
        task_ids = [task_a.id, task_b.id]

    response = client.delete(f"/api/v1/projects/{project_id}", headers=_auth_header(token))
    assert response.status_code == 200

    with app.app_context():
        assert Task.query.filter_by(project_id=project_id).count() == 0
        for task_id in task_ids:
            assert db.session.get(Task, task_id) is None


# ---- roles never bypass ownership ----------------------------------------


def test_admin_role_does_not_bypass_ownership(app, client):
    owner_token = _register_and_login(client, "owner@example.com")
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]

    admin_token = _make_admin_and_login(app, client)

    get_response = client.get(
        f"/api/v1/projects/{project_id}", headers=_auth_header(admin_token)
    )
    patch_response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Should Not Work"},
        headers=_auth_header(admin_token),
    )
    delete_response = client.delete(
        f"/api/v1/projects/{project_id}", headers=_auth_header(admin_token)
    )

    assert get_response.status_code == 403
    assert patch_response.status_code == 403
    assert delete_response.status_code == 403
    for response in (get_response, patch_response, delete_response):
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    still_there = client.get(
        f"/api/v1/projects/{project_id}", headers=_auth_header(owner_token)
    )
    assert still_there.status_code == 200
