from dataclasses import dataclass

from sqlalchemy import case, or_

from app.extensions.database import db
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.services.authorization_service import (
    AuthorizationDeniedError,
    require_permission,
    require_project_ownership,
    require_task_project_ownership,
)


class TaskNotFoundError(Exception):
    """Raised when a task does not exist."""


class TaskAccessDeniedError(Exception):
    """Raised when a user does not own a task's parent project."""


class TaskAssigneeNotFoundError(Exception):
    """Raised when a requested assignee does not exist."""


def _authorize_task(user: User, task: Task, permission: str) -> None:
    try:
        require_permission(user, permission)
        require_task_project_ownership(user, task)
    except AuthorizationDeniedError as error:
        raise TaskAccessDeniedError() from error


@dataclass(frozen=True)
class TaskPage:
    tasks: list[Task]
    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


def _validate_assignee(assigned_to: int | None) -> None:
    if assigned_to is not None and db.session.get(User, assigned_to) is None:
        raise TaskAssigneeNotFoundError()


def create_task(
    *,
    actor: User,
    project: Project,
    title: str,
    description: str | None = None,
    status: str = "pending",
    priority: str = "medium",
    assigned_to: int | None = None,
) -> Task:
    try:
        require_permission(actor, "task:create")
        require_project_ownership(actor, project)
        if assigned_to is not None:
            require_permission(actor, "task:assign")
    except AuthorizationDeniedError as error:
        raise TaskAccessDeniedError() from error
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


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_tasks_for_project(
    *,
    actor: User,
    project: Project,
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: int | None = None,
    search: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
) -> TaskPage:
    try:
        require_permission(actor, "task:view")
        require_project_ownership(actor, project)
    except AuthorizationDeniedError as error:
        raise TaskAccessDeniedError() from error
    query = Task.query.filter(Task.project_id == project.id)

    if status is not None:
        query = query.filter(Task.status == status)
    if priority is not None:
        query = query.filter(Task.priority == priority)
    if assigned_to is not None:
        query = query.filter(Task.assigned_to == assigned_to)
    if search is not None:
        pattern = f"%{_escape_like(search)}%"
        query = query.filter(
            or_(
                Task.title.ilike(pattern, escape="\\"),
                Task.description.ilike(pattern, escape="\\"),
            )
        )

    total_items = query.count()
    total_pages = (total_items + limit - 1) // limit

    priority_rank = case(
        (Task.priority == "low", 1),
        (Task.priority == "medium", 2),
        (Task.priority == "high", 3),
        else_=4,
    )
    sort_expressions = {
        "created_at": Task.created_at,
        "updated_at": Task.updated_at,
        "title": Task.title,
        "status": Task.status,
        "priority": priority_rank,
    }
    primary_sort = sort_expressions[sort]
    order_method = "asc" if order == "asc" else "desc"
    query = query.order_by(
        getattr(primary_sort, order_method)(), getattr(Task.id, order_method)()
    )
    tasks = query.offset((page - 1) * limit).limit(limit).all()

    return TaskPage(
        tasks=tasks,
        page=page,
        limit=limit,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


def get_task_for_project_owner(
    *, task_id: int, owner: User, permission: str = "task:view"
) -> Task:
    task = db.session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError()
    _authorize_task(owner, task, permission)

    return task


def update_task(*, actor: User, task: Task, updates: dict) -> Task:
    _authorize_task(actor, task, "task:update")
    if "assigned_to" in updates:
        try:
            require_permission(actor, "task:assign")
        except AuthorizationDeniedError as error:
            raise TaskAccessDeniedError() from error
        _validate_assignee(updates["assigned_to"])

    for field in ("title", "description", "status", "priority", "assigned_to"):
        if field in updates:
            setattr(task, field, updates[field])

    db.session.commit()

    return task


def delete_task(*, actor: User, task: Task) -> None:
    _authorize_task(actor, task, "task:delete")
    db.session.delete(task)
    db.session.commit()
