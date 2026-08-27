from flask import Blueprint

from app.utils.responses import success_response

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def get_health():
    return success_response(
        "Service is healthy",
        data={"service": "enterprise-task-management-api"},
    )
