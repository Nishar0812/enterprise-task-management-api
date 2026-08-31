from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app.schemas.task import (
    TaskCreateSchema,
    TaskQuerySchema,
    TaskSchema,
    TaskUpdateSchema,
)
from app.services.project_service import (
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    get_project_for_owner,
)
from app.services.task_service import (
    TaskAccessDeniedError,
    TaskAssigneeNotFoundError,
    TaskNotFoundError,
    create_task,
    delete_task,
    get_task_for_project_owner,
    list_tasks_for_project,
    update_task,
)
from app.utils.responses import error_response, success_response

tasks_bp = Blueprint("tasks", __name__)
project_tasks_bp = Blueprint("project_tasks", __name__)

_create_schema = TaskCreateSchema()
_update_schema = TaskUpdateSchema()
_task_schema = TaskSchema()
_tasks_schema = TaskSchema(many=True)
_query_schema = TaskQuerySchema()


def _project_error_response(error: Exception):
    if isinstance(error, ProjectNotFoundError):
        return error_response("Project not found", "NOT_FOUND", 404)
    return error_response(
        "You do not have permission to access this project", "FORBIDDEN", 403
    )


def _task_error_response(error: Exception):
    if isinstance(error, TaskNotFoundError):
        return error_response("Task not found", "NOT_FOUND", 404)
    return error_response(
        "You do not have permission to access this task", "FORBIDDEN", 403
    )


@project_tasks_bp.post("/<int:project_id>/tasks")
@jwt_required()
def create(project_id: int):
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
    try:
        project = get_project_for_owner(project_id=project_id, owner_id=owner_id)
        task = create_task(project=project, **data)
    except (ProjectNotFoundError, ProjectAccessDeniedError) as err:
        return _project_error_response(err)
    except TaskAssigneeNotFoundError:
        return error_response("Assigned user not found", "NOT_FOUND", 404)

    return success_response(
        "Task created successfully", data=_task_schema.dump(task), status_code=201
    )


@project_tasks_bp.get("/<int:project_id>/tasks")
@jwt_required()
def list_tasks(project_id: int):
    owner_id = int(get_jwt_identity())
    try:
        project = get_project_for_owner(project_id=project_id, owner_id=owner_id)
    except (ProjectNotFoundError, ProjectAccessDeniedError) as err:
        return _project_error_response(err)

    repeated = {
        key: ["Repeated query parameters are not allowed."]
        for key in request.args
        if len(request.args.getlist(key)) > 1
    }
    if repeated:
        return error_response(
            "Validation failed", "VALIDATION_ERROR", 400, data=repeated
        )

    try:
        query_params = _query_schema.load(request.args.to_dict(flat=True))
    except ValidationError as err:
        return error_response(
            "Validation failed", "VALIDATION_ERROR", 400, data=err.messages
        )

    result = list_tasks_for_project(project=project, **query_params)
    return success_response(
        "Tasks retrieved successfully",
        data={
            "tasks": _tasks_schema.dump(result.tasks),
            "pagination": {
                "page": result.page,
                "limit": result.limit,
                "total_items": result.total_items,
                "total_pages": result.total_pages,
                "has_next": result.has_next,
                "has_previous": result.has_previous,
            },
        },
    )


@tasks_bp.get("/<int:task_id>")
@jwt_required()
def get_task(task_id: int):
    owner_id = int(get_jwt_identity())
    try:
        task = get_task_for_project_owner(task_id=task_id, owner_id=owner_id)
    except (TaskNotFoundError, TaskAccessDeniedError) as err:
        return _task_error_response(err)

    return success_response(
        "Task retrieved successfully", data=_task_schema.dump(task)
    )


@tasks_bp.patch("/<int:task_id>")
@jwt_required()
def update(task_id: int):
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
        task = get_task_for_project_owner(task_id=task_id, owner_id=owner_id)
        task = update_task(task=task, updates=data)
    except (TaskNotFoundError, TaskAccessDeniedError) as err:
        return _task_error_response(err)
    except TaskAssigneeNotFoundError:
        return error_response("Assigned user not found", "NOT_FOUND", 404)

    return success_response(
        "Task updated successfully", data=_task_schema.dump(task)
    )


@tasks_bp.delete("/<int:task_id>")
@jwt_required()
def delete(task_id: int):
    owner_id = int(get_jwt_identity())
    try:
        task = get_task_for_project_owner(task_id=task_id, owner_id=owner_id)
    except (TaskNotFoundError, TaskAccessDeniedError) as err:
        return _task_error_response(err)

    delete_task(task=task)
    return success_response("Task deleted successfully", data=None)
