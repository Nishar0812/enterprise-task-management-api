from app.extensions.database import db
from app.models.project import Project
from app.models.user import User
from app.services.authorization_service import (
    AuthorizationDeniedError,
    require_permission,
    require_project_ownership,
)


class ProjectNotFoundError(Exception):
    """Raised when a project does not exist."""


class ProjectAccessDeniedError(Exception):
    """Raised when a user attempts to access a project they do not own."""


def _authorize_project(user: User, project: Project, permission: str) -> None:
    try:
        require_permission(user, permission)
        require_project_ownership(user, project)
    except AuthorizationDeniedError as error:
        raise ProjectAccessDeniedError() from error


def create_project(*, owner: User, name: str, description: str | None = None) -> Project:
    try:
        require_permission(owner, "project:create")
    except AuthorizationDeniedError as error:
        raise ProjectAccessDeniedError() from error

    project = Project(name=name, description=description, owner_id=owner.id)

    db.session.add(project)
    db.session.commit()

    return project


def list_projects_for_owner(*, owner: User) -> list[Project]:
    try:
        require_permission(owner, "project:view")
    except AuthorizationDeniedError as error:
        raise ProjectAccessDeniedError() from error
    return Project.query.filter_by(owner_id=owner.id).all()


def get_project_for_owner(
    *, project_id: int, owner: User, permission: str = "project:view"
) -> Project:
    project = db.session.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError()
    _authorize_project(owner, project, permission)

    return project


def update_project(*, actor: User, project: Project, updates: dict) -> Project:
    _authorize_project(actor, project, "project:update")
    for field in ("name", "description"):
        if field in updates:
            setattr(project, field, updates[field])

    db.session.commit()

    return project


def delete_project(*, actor: User, project: Project) -> None:
    _authorize_project(actor, project, "project:delete")
    db.session.delete(project)
    db.session.commit()
