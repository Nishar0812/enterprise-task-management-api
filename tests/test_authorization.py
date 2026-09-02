import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.models import User


PASSWORD = "StrongPassword123!"


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _make_user(app, email: str, role: str = "member") -> int:
    with app.app_context():
        user = User(name=role.title(), email=email, role=role)
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return response.get_json()["data"]["access_token"]


def _header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("identity", ["not-an-integer", "0", "-1"])
def test_invalid_jwt_identity_returns_401(app, client, identity):
    with app.app_context():
        token = create_access_token(identity=identity)

    response = client.get("/api/v1/users/me", headers=_header(token))

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_jwt_for_deleted_user_returns_401(app, client):
    user_id = _make_user(app, "deleted@example.com")
    token = _login(client, "deleted@example.com")
    with app.app_context():
        db.session.delete(db.session.get(User, user_id))
        db.session.commit()

    response = client.get("/api/v1/projects", headers=_header(token))

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("role", ["member", "manager"])
def test_non_admin_cannot_change_roles(app, client, role):
    actor_id = _make_user(app, f"{role}@example.com", role)
    target_id = _make_user(app, f"target-{role}@example.com")
    token = _login(client, f"{role}@example.com")

    response = client.patch(
        f"/api/v1/users/{target_id}/role",
        json={"role": "admin"},
        headers=_header(token),
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"
    with app.app_context():
        assert db.session.get(User, target_id).role == "member"
        assert db.session.get(User, actor_id).role == role


def test_member_cannot_promote_self(app, client):
    member_id = _make_user(app, "self-promote@example.com")
    token = _login(client, "self-promote@example.com")

    response = client.patch(
        f"/api/v1/users/{member_id}/role",
        json={"role": "admin"},
        headers=_header(token),
    )

    assert response.status_code == 403
    with app.app_context():
        assert db.session.get(User, member_id).role == "member"


def test_admin_can_change_role_without_exposing_password(app, client):
    _make_user(app, "admin@example.com", "admin")
    target_id = _make_user(app, "target@example.com")
    token = _login(client, "admin@example.com")

    response = client.patch(
        f"/api/v1/users/{target_id}/role",
        json={"role": "manager"},
        headers=_header(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["role"] == "manager"
    assert "password" not in response.get_data(as_text=True)
    assert "password_hash" not in response.get_data(as_text=True)


def test_role_change_applies_to_already_issued_token(app, client):
    _make_user(app, "admin@example.com", "admin")
    manager_id = _make_user(app, "manager@example.com", "manager")
    target_id = _make_user(app, "target@example.com")
    admin_token = _login(client, "admin@example.com")
    manager_token = _login(client, "manager@example.com")

    promoted = client.patch(
        f"/api/v1/users/{manager_id}/role",
        json={"role": "admin"},
        headers=_header(admin_token),
    )
    changed_by_promoted_user = client.patch(
        f"/api/v1/users/{target_id}/role",
        json={"role": "manager"},
        headers=_header(manager_token),
    )

    assert promoted.status_code == 200
    assert changed_by_promoted_user.status_code == 200


def test_last_admin_cannot_be_demoted(app, client):
    admin_id = _make_user(app, "admin@example.com", "admin")
    token = _login(client, "admin@example.com")

    response = client.patch(
        f"/api/v1/users/{admin_id}/role",
        json={"role": "member"},
        headers=_header(token),
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "LAST_ADMIN_REQUIRED"
    with app.app_context():
        assert db.session.get(User, admin_id).role == "admin"


def test_admin_can_be_demoted_when_another_admin_exists(app, client):
    first_admin_id = _make_user(app, "first-admin@example.com", "admin")
    _make_user(app, "second-admin@example.com", "admin")
    token = _login(client, "first-admin@example.com")

    response = client.patch(
        f"/api/v1/users/{first_admin_id}/role",
        json={"role": "manager"},
        headers=_header(token),
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["role"] == "manager"


@pytest.mark.parametrize(
    "payload",
    [{}, {"role": "superuser"}, {"role": "ADMIN"}, {"role": "member", "admin": True}],
)
def test_invalid_role_change_is_rejected(app, client, payload):
    _make_user(app, "admin@example.com", "admin")
    target_id = _make_user(app, "target@example.com")
    token = _login(client, "admin@example.com")

    response = client.patch(
        f"/api/v1/users/{target_id}/role", json=payload, headers=_header(token)
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_role_change_requires_authentication(client):
    response = client.patch("/api/v1/users/1/role", json={"role": "manager"})

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_role_change_for_unknown_user_returns_404(app, client):
    _make_user(app, "admin@example.com", "admin")
    token = _login(client, "admin@example.com")

    response = client.patch(
        "/api/v1/users/9999/role",
        json={"role": "manager"},
        headers=_header(token),
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("role", ["member", "manager", "admin"])
def test_each_role_can_manage_resources_it_owns(app, client, role):
    email = f"owner-{role}@example.com"
    _make_user(app, email, role)
    token = _login(client, email)

    project_response = client.post(
        "/api/v1/projects",
        json={"name": f"{role} project"},
        headers=_header(token),
    )
    project_id = project_response.get_json()["data"]["id"]
    task_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": f"{role} task"},
        headers=_header(token),
    )

    assert project_response.status_code == 201
    assert task_response.status_code == 201
    assert client.get(
        f"/api/v1/projects/{project_id}", headers=_header(token)
    ).status_code == 200
    assert client.get(
        f"/api/v1/tasks/{task_response.get_json()['data']['id']}",
        headers=_header(token),
    ).status_code == 200


def test_manager_cannot_bypass_project_ownership_for_mutations(app, client):
    _make_user(app, "owner@example.com")
    _make_user(app, "manager@example.com", "manager")
    owner_token = _login(client, "owner@example.com")
    manager_token = _login(client, "manager@example.com")
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "Owner project"},
        headers=_header(owner_token),
    ).get_json()["data"]["id"]

    patch_response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Hijacked"},
        headers=_header(manager_token),
    )
    delete_response = client.delete(
        f"/api/v1/projects/{project_id}", headers=_header(manager_token)
    )

    assert patch_response.status_code == 403
    assert delete_response.status_code == 403
    still_owned = client.get(
        f"/api/v1/projects/{project_id}", headers=_header(owner_token)
    )
    assert still_owned.status_code == 200
    assert still_owned.get_json()["data"]["name"] == "Owner project"
