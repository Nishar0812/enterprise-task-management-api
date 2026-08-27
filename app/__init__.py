from flask import Flask

from app.config import get_config
from app.extensions import db, jwt, migrate
from app.routes import register_blueprints
from app.utils.errors import register_error_handlers


def create_app(env_name: str | None = None) -> Flask:
    app = Flask(__name__)
    config = get_config(env_name)
    app.config.from_object(config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    with app.app_context():
        from app import models  # noqa: F401  ensures models are registered with SQLAlchemy

    register_blueprints(app, config.API_VERSION_PREFIX)
    register_error_handlers(app)

    return app
