import logging

from flask import Flask
from werkzeug.exceptions import HTTPException

from app.utils.responses import error_response

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def handle_bad_request(_error: HTTPException):
        return error_response("Bad request", "BAD_REQUEST", 400)

    @app.errorhandler(404)
    def handle_not_found(_error: HTTPException):
        return error_response("Resource not found", "NOT_FOUND", 404)

    @app.errorhandler(500)
    def handle_internal_error(error: Exception):
        logger.exception("Unhandled server error", exc_info=error)
        return error_response("Internal server error", "INTERNAL_SERVER_ERROR", 500)
