from flask import Flask

from app.routes.auth import auth_bp
from app.routes.health import health_bp
from app.routes.projects import projects_bp
from app.routes.tasks import tasks_bp
from app.routes.users import users_bp


def register_blueprints(app: Flask, url_prefix: str) -> None:
    app.register_blueprint(health_bp, url_prefix=url_prefix)
    app.register_blueprint(auth_bp, url_prefix=f"{url_prefix}/auth")
    app.register_blueprint(users_bp, url_prefix=f"{url_prefix}/users")
    app.register_blueprint(projects_bp, url_prefix=f"{url_prefix}/projects")
    app.register_blueprint(tasks_bp, url_prefix=f"{url_prefix}/tasks")
