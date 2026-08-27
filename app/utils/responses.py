from typing import Any

from flask import jsonify
from flask.wrappers import Response


def success_response(
    message: str, data: Any = None, status_code: int = 200
) -> tuple[Response, int]:
    payload = {"success": True, "message": message, "data": data, "error": None}
    return jsonify(payload), status_code


def error_response(
    message: str, code: str, status_code: int = 400, data: Any = None
) -> tuple[Response, int]:
    payload = {
        "success": False,
        "message": message,
        "data": data,
        "error": {"code": code},
    }
    return jsonify(payload), status_code
