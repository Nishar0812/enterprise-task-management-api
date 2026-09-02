from flask_jwt_extended import JWTManager

from app.extensions.database import db
from app.models.user import User
from app.utils.responses import error_response

jwt = JWTManager()


@jwt.unauthorized_loader
def _handle_missing_token(_reason: str):
    return error_response(
        "Missing or invalid authentication token", "UNAUTHORIZED", 401
    )


@jwt.invalid_token_loader
def _handle_invalid_token(_reason: str):
    return error_response(
        "Missing or invalid authentication token", "UNAUTHORIZED", 401
    )


@jwt.expired_token_loader
def _handle_expired_token(_jwt_header: dict, _jwt_payload: dict):
    return error_response("Authentication token has expired", "TOKEN_EXPIRED", 401)


@jwt.user_lookup_loader
def _load_authenticated_user(_jwt_header: dict, jwt_payload: dict):
    """Resolve a JWT subject to a current database user without conversion errors."""
    try:
        user_id = int(jwt_payload.get("sub"))
    except (TypeError, ValueError):
        return None

    if user_id < 1:
        return None
    return db.session.get(User, user_id)


@jwt.user_lookup_error_loader
def _handle_user_lookup_error(_jwt_header: dict, _jwt_payload: dict):
    return error_response(
        "Authentication token does not identify a valid user", "UNAUTHORIZED", 401
    )
