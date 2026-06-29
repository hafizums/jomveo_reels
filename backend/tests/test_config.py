from pathlib import Path

from backend.app.core.config import Settings


def test_settings_have_local_development_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "JomVeo Reels API"
    assert settings.api_v1_prefix == "/api"
    assert isinstance(settings.generated_root, Path)
    assert "http://localhost:5173" in settings.cors_allowed_origins


def test_settings_load_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
