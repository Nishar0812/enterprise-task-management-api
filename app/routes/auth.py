from flask import Blueprint, request
from flask_jwt_extended import create_access_token
from marshmallow import ValidationError

from app.schemas.auth import LoginRequestSchema, RegisterRequestSchema, UserSchema
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)
from app.utils.responses import error_response, success_response

auth_bp = Blueprint("auth", __name__)

_register_schema = RegisterRequestSchema()
_login_schema = LoginRequestSchema()
_user_schema = UserSchema()


@auth_bp.post("/register")
def register():
    json_data = request.get_json(silent=True)
    if json_data is None:
        return error_response("Request body must be valid JSON", "INVALID_JSON", 400)

    try:
        data = _register_schema.load(json_data)
    except ValidationError as err:
        return error_response(
            "Validation failed", "VALIDATION_ERROR", 400, data=err.messages
        )

    try:
        user = register_user(
            name=data["name"], email=data["email"], password=data["password"]
        )
    except EmailAlreadyRegisteredError:
        return error_response(
            "Email is already registered", "EMAIL_ALREADY_EXISTS", 409
        )

    return success_response(
        "User registered successfully",
        data=_user_schema.dump(user),
        status_code=201,
    )


@auth_bp.post("/login")
def login():
    json_data = request.get_json(silent=True)
    if json_data is None:
        return error_response("Request body must be valid JSON", "INVALID_JSON", 400)

    try:
        data = _login_schema.load(json_data)
    except ValidationError as err:
        return error_response(
            "Validation failed", "VALIDATION_ERROR", 400, data=err.messages
        )

    try:
        user = authenticate_user(email=data["email"], password=data["password"])
    except InvalidCredentialsError:
        return error_response(
            "Invalid email or password", "INVALID_CREDENTIALS", 401
        )

    access_token = create_access_token(identity=str(user.id))

    return success_response(
        "Login successful",
        data={"access_token": access_token, "user": _user_schema.dump(user)},
    )
