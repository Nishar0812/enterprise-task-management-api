from flask import Blueprint, request
from flask_jwt_extended import current_user, jwt_required
from marshmallow import ValidationError

from app.schemas.auth import RoleUpdateSchema, UserSchema
from app.services.auth_service import (
    LastAdminError,
    UserNotFoundError,
    change_user_role,
)
from app.services.authorization_service import AuthorizationDeniedError
from app.utils.responses import error_response, success_response

users_bp = Blueprint("users", __name__)

_user_schema = UserSchema()
_role_update_schema = RoleUpdateSchema()


@users_bp.get("/me")
@jwt_required()
def get_current_user():
    return success_response(
        "User retrieved successfully", data=_user_schema.dump(current_user)
    )


@users_bp.patch("/<int:user_id>/role")
@jwt_required()
def update_user_role(user_id: int):
    json_data = request.get_json(silent=True)
    if json_data is None:
        return error_response("Request body must be valid JSON", "INVALID_JSON", 400)

    try:
        data = _role_update_schema.load(json_data)
    except ValidationError as err:
        return error_response(
            "Validation failed", "VALIDATION_ERROR", 400, data=err.messages
        )

    try:
        user = change_user_role(
            actor=current_user, user_id=user_id, new_role=data["role"]
        )
    except AuthorizationDeniedError:
        return error_response(
            "You do not have permission to change user roles", "FORBIDDEN", 403
        )
    except UserNotFoundError:
        return error_response("User not found", "NOT_FOUND", 404)
    except LastAdminError:
        return error_response(
            "The last admin cannot be demoted", "LAST_ADMIN_REQUIRED", 409
        )

    return success_response(
        "User role updated successfully", data=_user_schema.dump(user)
    )
