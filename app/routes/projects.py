from flask import Blueprint, request
from flask_jwt_extended import current_user, jwt_required
from marshmallow import ValidationError

from app.schemas.project import ProjectCreateSchema, ProjectSchema, ProjectUpdateSchema
from app.services.project_service import (
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    create_project,
    delete_project,
    get_project_for_owner,
    list_projects_for_owner,
    update_project,
)
from app.utils.responses import error_response, success_response

projects_bp = Blueprint("projects", __name__)

_create_schema = ProjectCreateSchema()
_update_schema = ProjectUpdateSchema()
_project_schema = ProjectSchema()
_projects_schema = ProjectSchema(many=True)


@projects_bp.post("")
@jwt_required()
def create():
    json_data = request.get_json(silent=True)
    if json_data is None:
        return error_response("Request body must be valid JSON", "INVALID_JSON", 400)

    try:
        data = _create_schema.load(json_data)
    except ValidationError as err:
        return error_response(
            "Validation failed", "VALIDATION_ERROR", 400, data=err.messages
        )

    project = create_project(
        owner=current_user, name=data["name"], description=data["description"]
    )

    return success_response(
        "Project created successfully",
        data=_project_schema.dump(project),
        status_code=201,
    )


@projects_bp.get("")
@jwt_required()
def list_projects():
    projects = list_projects_for_owner(owner=current_user)

    return success_response(
        "Projects retrieved successfully", data=_projects_schema.dump(projects)
    )


@projects_bp.get("/<int:project_id>")
@jwt_required()
def get_project(project_id: int):
    try:
        project = get_project_for_owner(project_id=project_id, owner=current_user)
    except ProjectNotFoundError:
        return error_response("Project not found", "NOT_FOUND", 404)
    except ProjectAccessDeniedError:
        return error_response(
            "You do not have permission to access this project", "FORBIDDEN", 403
        )

    return success_response(
        "Project retrieved successfully", data=_project_schema.dump(project)
    )


@projects_bp.patch("/<int:project_id>")
@jwt_required()
def update(project_id: int):
    json_data = request.get_json(silent=True)
    if json_data is None:
        return error_response("Request body must be valid JSON", "INVALID_JSON", 400)

    try:
        data = _update_schema.load(json_data)
    except ValidationError as err:
        return error_response(
            "Validation failed", "VALIDATION_ERROR", 400, data=err.messages
        )

    try:
        project = get_project_for_owner(
            project_id=project_id, owner=current_user, permission="project:update"
        )
    except ProjectNotFoundError:
        return error_response("Project not found", "NOT_FOUND", 404)
    except ProjectAccessDeniedError:
        return error_response(
            "You do not have permission to access this project", "FORBIDDEN", 403
        )

    project = update_project(actor=current_user, project=project, updates=data)

    return success_response(
        "Project updated successfully", data=_project_schema.dump(project)
    )


@projects_bp.delete("/<int:project_id>")
@jwt_required()
def delete(project_id: int):
    try:
        project = get_project_for_owner(
            project_id=project_id, owner=current_user, permission="project:delete"
        )
    except ProjectNotFoundError:
        return error_response("Project not found", "NOT_FOUND", 404)
    except ProjectAccessDeniedError:
        return error_response(
            "You do not have permission to access this project", "FORBIDDEN", 403
        )

    delete_project(actor=current_user, project=project)

    return success_response("Project deleted successfully", data=None)
