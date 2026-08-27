import pytest

from app import create_app
from app.config.settings import get_config


def test_production_config_fails_fast_without_required_env_vars(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        get_config("production")


def test_production_config_succeeds_with_required_env_vars(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

    config = get_config("production")

    assert config.__name__ == "ProductionConfig"


def test_create_app_fails_fast_in_production_without_env_vars(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError):
        create_app("production")


def test_development_config_does_not_require_env_vars(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    config = get_config("development")

    assert config.__name__ == "DevelopmentConfig"
