from app.extensions.database import db
from app.models.project import Project
from app.models.task import Task
from app.models.user import User


class TaskNotFoundError(Exception):
    """Raised when a task does not exist."""


class TaskAccessDeniedError(Exception):
    """Raised when a user does not own a task's parent project."""


class TaskAssigneeNotFoundError(Exception):
    """Raised when a requested assignee does not exist."""


def _validate_assignee(assigned_to: int | None) -> None:
    if assigned_to is not None and db.session.get(User, assigned_to) is None:
        raise TaskAssigneeNotFoundError()


def create_task(
    *,
    project: Project,
    title: str,
    description: str | None = None,
    status: str = "pending",
    priority: str = "medium",
    assigned_to: int | None = None,
) -> Task:
    _validate_assignee(assigned_to)
    task = Task(
        title=title,
        description=description,
        status=status,
        priority=priority,
        project_id=project.id,
        assigned_to=assigned_to,
    )

    db.session.add(task)
    db.session.commit()

    return task


def list_tasks_for_project(*, project: Project) -> list[Task]:
    return Task.query.filter_by(project_id=project.id).all()


def get_task_for_project_owner(*, task_id: int, owner_id: int) -> Task:
    task = db.session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError()
    if task.project.owner_id != owner_id:
        raise TaskAccessDeniedError()

    return task


def update_task(*, task: Task, updates: dict) -> Task:
    if "assigned_to" in updates:
        _validate_assignee(updates["assigned_to"])

    for field in ("title", "description", "status", "priority", "assigned_to"):
        if field in updates:
            setattr(task, field, updates[field])

    db.session.commit()

    return task


def delete_task(*, task: Task) -> None:
    db.session.delete(task)
    db.session.commit()
