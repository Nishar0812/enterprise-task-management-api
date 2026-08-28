from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.schemas.auth import UserSchema
from app.services.auth_service import get_user_by_id
from app.utils.responses import error_response, success_response

users_bp = Blueprint("users", __name__)

_user_schema = UserSchema()


@users_bp.get("/me")
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = get_user_by_id(int(user_id))
    if user is None:
        return error_response("User not found", "NOT_FOUND", 404)

    return success_response(
        "User retrieved successfully", data=_user_schema.dump(user)
    )
