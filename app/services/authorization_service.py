from app.models.project import Project
from app.models.task import Task
from app.models.user import User


class AuthorizationDeniedError(Exception):
    """Raised when an authenticated user is not allowed to perform an action."""


ROLE_PERMISSIONS = {
    "admin": frozenset(
        {
            "project:create",
            "project:view",
            "project:update",
            "project:delete",
            "task:create",
            "task:view",
            "task:update",
            "task:delete",
            "task:assign",
            "user:change_role",
        }
    ),
    "manager": frozenset(
        {
            "project:create",
            "project:view",
            "project:update",
            "project:delete",
            "task:create",
            "task:view",
            "task:update",
            "task:delete",
            "task:assign",
        }
    ),
    "member": frozenset(
        {
            "project:create",
            "project:view",
            "project:update",
            "project:delete",
            "task:create",
            "task:view",
            "task:update",
            "task:delete",
            "task:assign",
        }
    ),
}


def require_permission(user: User, permission: str) -> None:
    """Require an explicitly granted role permission; unknown roles default-deny."""
    if permission not in ROLE_PERMISSIONS.get(user.role, frozenset()):
        raise AuthorizationDeniedError()


def require_project_ownership(user: User, project: Project) -> None:
    """Enforce the M3 project-owner boundary independently from role permissions."""
    if project.owner_id != user.id:
        raise AuthorizationDeniedError()


def require_task_project_ownership(user: User, task: Task) -> None:
    """Enforce the M4 parent-project-owner boundary; assignment grants no access."""
    require_project_ownership(user, task.project)
