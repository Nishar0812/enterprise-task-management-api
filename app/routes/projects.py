from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
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

    owner_id = int(get_jwt_identity())
    project = create_project(
        owner_id=owner_id, name=data["name"], description=data["description"]
    )

    return success_response(
        "Project created successfully",
        data=_project_schema.dump(project),
        status_code=201,
    )


@projects_bp.get("")
@jwt_required()
def list_projects():
    owner_id = int(get_jwt_identity())
    projects = list_projects_for_owner(owner_id=owner_id)

    return success_response(
        "Projects retrieved successfully", data=_projects_schema.dump(projects)
    )


@projects_bp.get("/<int:project_id>")
@jwt_required()
def get_project(project_id: int):
    owner_id = int(get_jwt_identity())

    try:
        project = get_project_for_owner(project_id=project_id, owner_id=owner_id)
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

    owner_id = int(get_jwt_identity())

    try:
        project = get_project_for_owner(project_id=project_id, owner_id=owner_id)
    except ProjectNotFoundError:
        return error_response("Project not found", "NOT_FOUND", 404)
    except ProjectAccessDeniedError:
        return error_response(
            "You do not have permission to access this project", "FORBIDDEN", 403
        )

    project = update_project(project=project, updates=data)

    return success_response(
        "Project updated successfully", data=_project_schema.dump(project)
    )


@projects_bp.delete("/<int:project_id>")
@jwt_required()
def delete(project_id: int):
    owner_id = int(get_jwt_identity())

    try:
        project = get_project_for_owner(project_id=project_id, owner_id=owner_id)
    except ProjectNotFoundError:
        return error_response("Project not found", "NOT_FOUND", 404)
    except ProjectAccessDeniedError:
        return error_response(
            "You do not have permission to access this project", "FORBIDDEN", 403
        )

    delete_project(project=project)

    return success_response("Project deleted successfully", data=None)
