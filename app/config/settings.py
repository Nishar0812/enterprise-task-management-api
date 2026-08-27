import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///dev.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    API_TITLE = "Enterprise Task Management API"
    API_VERSION_PREFIX = "/api/v1"


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    PROPAGATE_EXCEPTIONS = False


class ProductionConfig(BaseConfig):
    DEBUG = False


REQUIRED_PRODUCTION_ENV_VARS = ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL")


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None) -> type[BaseConfig]:
    env_name = env_name or os.environ.get("FLASK_ENV", "development")
    config = CONFIG_MAP.get(env_name, DevelopmentConfig)

    if config is ProductionConfig:
        missing = [var for var in REQUIRED_PRODUCTION_ENV_VARS if not os.environ.get(var)]
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s) for production: "
                + ", ".join(missing)
            )

    return config
