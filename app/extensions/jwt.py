from flask_jwt_extended import JWTManager

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
