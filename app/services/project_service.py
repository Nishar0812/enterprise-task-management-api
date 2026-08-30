from app.extensions.database import db
from app.models.project import Project


class ProjectNotFoundError(Exception):
    """Raised when a project does not exist."""


class ProjectAccessDeniedError(Exception):
    """Raised when a user attempts to access a project they do not own."""


def create_project(*, owner_id: int, name: str, description: str | None = None) -> Project:
    project = Project(name=name, description=description, owner_id=owner_id)

    db.session.add(project)
    db.session.commit()

    return project


def list_projects_for_owner(*, owner_id: int) -> list[Project]:
    return Project.query.filter_by(owner_id=owner_id).all()


def get_project_for_owner(*, project_id: int, owner_id: int) -> Project:
    project = db.session.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError()
    if project.owner_id != owner_id:
        raise ProjectAccessDeniedError()

    return project


def update_project(*, project: Project, updates: dict) -> Project:
    for field in ("name", "description"):
        if field in updates:
            setattr(project, field, updates[field])

    db.session.commit()

    return project


def delete_project(*, project: Project) -> None:
    db.session.delete(project)
    db.session.commit()
