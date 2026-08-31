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
    data = response.get_json()["data"]
    assert {task["title"] for task in data["tasks"]} == {
        "First",
        "Second",
    }
    assert data["pagination"] == {
        "page": 1,
        "limit": 20,
        "total_items": 2,
        "total_pages": 1,
        "has_next": False,
        "has_previous": False,
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

    tasks = response.get_json()["data"]["tasks"]
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


def _list_tasks(client, token, project_id, query=""):
    response = client.get(
        f"/api/v1/projects/{project_id}/tasks{query}", headers=_auth_header(token)
    )
    return response, response.get_json()


def test_task_pagination_first_middle_last_and_beyond(client):
    token = _register_and_login(client, "paging@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    for number in range(5):
        _create_task(client, token, project_id, title=f"Task {number}")

    expected_lengths = {1: 2, 2: 2, 3: 1, 4: 0}
    seen = []
    for page, expected_length in expected_lengths.items():
        response, body = _list_tasks(client, token, project_id, f"?page={page}&limit=2")
        assert response.status_code == 200
        assert len(body["data"]["tasks"]) == expected_length
        pagination = body["data"]["pagination"]
        assert pagination["total_items"] == 5
        assert pagination["total_pages"] == 3
        assert pagination["has_next"] is (page < 3)
        assert pagination["has_previous"] is (page > 1)
        seen.extend(task["id"] for task in body["data"]["tasks"])

    assert len(seen) == len(set(seen)) == 5


def test_task_pagination_empty_project_and_limit_100(client):
    token = _register_and_login(client, "empty@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response, body = _list_tasks(client, token, project_id, "?limit=100")

    assert response.status_code == 200
    assert body["data"] == {
        "tasks": [],
        "pagination": {
            "page": 1,
            "limit": 100,
            "total_items": 0,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False,
        },
    }


@pytest.mark.parametrize(
    "query",
    [
        "?page=0",
        "?page=-1",
        "?page=1.5",
        "?page=nope",
        "?limit=0",
        "?limit=-1",
        "?limit=1.5",
        "?limit=nope",
        "?limit=101",
        "?assigned_to=0",
        "?assigned_to=-1",
        "?assigned_to=nope",
        "?status=archived",
        "?priority=urgent",
        "?sort=id",
        "?order=sideways",
        "?search=%20%20%20",
        f"?search={'x' * 201}",
        "?unknown=value",
        "?page=1&page=2",
    ],
)
def test_invalid_task_query_parameters_return_validation_error(client, query):
    token = _register_and_login(client, "validation@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]

    response, body = _list_tasks(client, token, project_id, query)

    assert response.status_code == 400
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("status", ["pending", "in_progress", "completed"])
def test_filter_tasks_by_status(client, status):
    token = _register_and_login(client, f"{status}@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    for value in ("pending", "in_progress", "completed"):
        _create_task(client, token, project_id, title=value, status=value)

    response, body = _list_tasks(client, token, project_id, f"?status={status}")

    assert response.status_code == 200
    assert [task["status"] for task in body["data"]["tasks"]] == [status]


@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_filter_tasks_by_priority(client, priority):
    token = _register_and_login(client, f"filter-{priority}@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    for value in ("low", "medium", "high"):
        _create_task(client, token, project_id, title=value, priority=value)

    response, body = _list_tasks(client, token, project_id, f"?priority={priority}")

    assert response.status_code == 200
    assert [task["priority"] for task in body["data"]["tasks"]] == [priority]


def test_assignee_and_combined_filters(client):
    token = _register_and_login(client, "combined@example.com")
    _register_and_login(client, "combined-assignee@example.com")
    with client.application.app_context():
        assignee_id = User.query.filter_by(email="combined-assignee@example.com").one().id
    project_id = _create_project(client, token).get_json()["data"]["id"]
    _create_task(
        client, token, project_id, title="Match", status="pending",
        priority="high", assigned_to=assignee_id,
    )
    _create_task(client, token, project_id, title="Other", status="completed")

    query = f"?status=pending&priority=high&assigned_to={assignee_id}"
    response, body = _list_tasks(client, token, project_id, query)
    missing_response, missing_body = _list_tasks(
        client, token, project_id, "?assigned_to=99999"
    )

    assert response.status_code == 200
    assert [task["title"] for task in body["data"]["tasks"]] == ["Match"]
    assert missing_response.status_code == 200
    assert missing_body["data"]["pagination"]["total_items"] == 0


def test_searches_title_and_description_case_insensitively(client):
    token = _register_and_login(client, "search@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    _create_task(client, token, project_id, title="AUTHENTICATION endpoint")
    _create_task(client, token, project_id, title="Docs", description="Authentication guide")
    _create_task(client, token, project_id, title="Unrelated", description=None)

    response, body = _list_tasks(client, token, project_id, "?search=%20authentication%20")

    assert response.status_code == 200
    assert {task["title"] for task in body["data"]["tasks"]} == {
        "AUTHENTICATION endpoint", "Docs"
    }


@pytest.mark.parametrize(
    ("search", "matching_title"), [("%", "Uses % literally"), ("_", "Uses _ literally")]
)
def test_search_treats_sql_wildcards_literally(client, search, matching_title):
    token = _register_and_login(client, f"wild-{ord(search)}@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    _create_task(client, token, project_id, title=matching_title)
    _create_task(client, token, project_id, title="Ordinary")

    response, body = _list_tasks(client, token, project_id, f"?search={search}")

    assert response.status_code == 200
    assert [task["title"] for task in body["data"]["tasks"]] == [matching_title]


def test_search_combines_with_filter_and_can_return_zero_results(client):
    token = _register_and_login(client, "search-filter@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    _create_task(client, token, project_id, title="Needle", status="pending")
    _create_task(client, token, project_id, title="Needle done", status="completed")

    _, matching = _list_tasks(client, token, project_id, "?search=needle&status=completed")
    _, empty = _list_tasks(client, token, project_id, "?search=missing")

    assert [task["title"] for task in matching["data"]["tasks"]] == ["Needle done"]
    assert empty["data"]["tasks"] == []
    assert empty["data"]["pagination"]["total_items"] == 0


@pytest.mark.parametrize("sort", ["created_at", "updated_at", "title", "status"])
@pytest.mark.parametrize("order", ["asc", "desc"])
def test_allowed_task_sorting(client, sort, order):
    token = _register_and_login(client, f"sort-{sort}-{order}@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    _create_task(client, token, project_id, title="Bravo", status="pending")
    _create_task(client, token, project_id, title="Alpha", status="completed")

    response, body = _list_tasks(client, token, project_id, f"?sort={sort}&order={order}")

    assert response.status_code == 200
    values = [task[sort] for task in body["data"]["tasks"]]
    assert values == sorted(values, reverse=order == "desc")


@pytest.mark.parametrize(
    ("order", "expected"),
    [("asc", ["low", "medium", "high"]), ("desc", ["high", "medium", "low"])],
)
def test_priority_sort_uses_business_rank(client, order, expected):
    token = _register_and_login(client, f"rank-{order}@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    for priority in ("medium", "high", "low"):
        _create_task(client, token, project_id, title=priority, priority=priority)

    _, body = _list_tasks(client, token, project_id, f"?sort=priority&order={order}")

    assert [task["priority"] for task in body["data"]["tasks"]] == expected


def test_sort_uses_id_as_deterministic_tie_breaker(client):
    token = _register_and_login(client, "tie@example.com")
    project_id = _create_project(client, token).get_json()["data"]["id"]
    first = _create_task(client, token, project_id, title="Same").get_json()["data"]["id"]
    second = _create_task(client, token, project_id, title="Same").get_json()["data"]["id"]

    _, ascending = _list_tasks(client, token, project_id, "?sort=title&order=asc")
    _, descending = _list_tasks(client, token, project_id, "?sort=title&order=desc")

    assert [task["id"] for task in ascending["data"]["tasks"]] == [first, second]
    assert [task["id"] for task in descending["data"]["tasks"]] == [second, first]


def test_task_query_features_remain_project_scoped(client):
    owner_token = _register_and_login(client, "scope-owner@example.com")
    other_token = _register_and_login(client, "scope-other@example.com")
    owner_project = _create_project(client, owner_token).get_json()["data"]["id"]
    other_project = _create_project(client, other_token).get_json()["data"]["id"]
    _create_task(client, owner_token, owner_project, title="Needle", priority="high")
    _create_task(client, other_token, other_project, title="Needle", priority="high")

    response, body = _list_tasks(
        client, owner_token, owner_project, "?search=needle&priority=high&page=1&limit=100"
    )
    forbidden, forbidden_body = _list_tasks(
        client, owner_token, other_project, "?search=needle&page=99&limit=100"
    )

    assert response.status_code == 200
    assert body["data"]["pagination"]["total_items"] == 1
    assert {task["project_id"] for task in body["data"]["tasks"]} == {owner_project}
    assert forbidden.status_code == 403
    assert forbidden_body["data"] is None


def test_manager_and_assignee_cannot_bypass_project_ownership(app, client):
    owner_token = _register_and_login(client, "access-owner@example.com")
    assignee_token = _register_and_login(client, "access-assignee@example.com")
    with app.app_context():
        assignee = User.query.filter_by(email="access-assignee@example.com").one()
        manager = User(name="Manager", email="manager@example.com", role="manager")
        manager.set_password("StrongPassword123!")
        db.session.add(manager)
        db.session.commit()
        assignee_id = assignee.id
    manager_token = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@example.com", "password": "StrongPassword123!"},
    ).get_json()["data"]["access_token"]
    project_id = _create_project(client, owner_token).get_json()["data"]["id"]
    _create_task(client, owner_token, project_id, assigned_to=assignee_id)

    assert _list_tasks(client, assignee_token, project_id, "?assigned_to=1")[0].status_code == 403
    assert _list_tasks(client, manager_token, project_id, "?page=1&limit=100")[0].status_code == 403
