from datetime import datetime, timezone

import pytest
import sqlalchemy.exc

from app import create_app
from app.extensions import db
from app.models import Project, Task, User


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application


def _make_user(email: str, role: str = "member") -> User:
    user = User(name="Test User", email=email, role=role)
    user.set_password("password123")
    return user


def test_invalid_role_is_rejected(app):
    with app.app_context():
        db.session.add(_make_user("bad-role@example.com", role="superuser"))
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_valid_roles_are_accepted(app):
    with app.app_context():
        for role in ("admin", "manager", "member"):
            db.session.add(_make_user(f"{role}@example.com", role=role))
        db.session.commit()

        assert User.query.count() == 3


def test_invalid_task_status_is_rejected(app):
    with app.app_context():
        owner = _make_user("owner-status@example.com")
        db.session.add(owner)
        db.session.commit()
        project = Project(name="P", owner_id=owner.id)
        db.session.add(project)
        db.session.commit()

        db.session.add(Task(title="bad", project_id=project.id, status="archived"))
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_invalid_task_priority_is_rejected(app):
    with app.app_context():
        owner = _make_user("owner-priority@example.com")
        db.session.add(owner)
        db.session.commit()
        project = Project(name="P", owner_id=owner.id)
        db.session.add(project)
        db.session.commit()

        db.session.add(Task(title="bad", project_id=project.id, priority="urgent"))
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_timestamps_are_timezone_aware_after_reload(app):
    with app.app_context():
        user = _make_user("tz@example.com")
        db.session.add(user)
        db.session.commit()
        db.session.expire_all()

        reloaded = db.session.get(User, user.id)

        assert reloaded.created_at.tzinfo is not None
        assert reloaded.updated_at.tzinfo is not None
        # A naive/aware mismatch here would raise TypeError.
        assert reloaded.created_at <= datetime.now(timezone.utc)


def test_deleting_user_who_owns_project_is_blocked(app):
    with app.app_context():
        owner = _make_user("owner-delete@example.com")
        db.session.add(owner)
        db.session.commit()
        project = Project(name="Protected", owner_id=owner.id)
        db.session.add(project)
        db.session.commit()

        db.session.delete(owner)
        with pytest.raises(ValueError, match="still owns"):
            db.session.commit()
        db.session.rollback()

        assert db.session.get(User, owner.id) is not None
        assert db.session.get(Project, project.id) is not None


def test_deleting_user_without_projects_succeeds(app):
    with app.app_context():
        user = _make_user("lone-user@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        db.session.delete(user)
        db.session.commit()

        assert db.session.get(User, user_id) is None
