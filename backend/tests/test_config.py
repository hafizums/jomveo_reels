from pathlib import Path

from backend.app.core.config import Settings


def test_settings_have_local_development_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "JomVeo Reels API"
    assert settings.api_v1_prefix == "/api"
    assert isinstance(settings.generated_root, Path)
    assert "http://localhost:5173" in settings.cors_allowed_origins
    assert settings.database_url == "sqlite:///backend/generated/jomveo.db"
    assert settings.queue_backend == "inline"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.job_default_timeout_seconds == 1800
    assert settings.job_max_attempts == 3
    assert settings.job_retry_backoff_seconds == 30
    assert settings.job_stale_after_seconds == 900
    assert settings.job_worker_id == "local-worker"
    assert settings.storage_backend == "local"
    assert settings.local_storage_root.name == "generated"
    assert settings.public_generated_url_prefix == "/generated"
    assert settings.max_upload_bytes == 100 * 1024 * 1024
    assert settings.max_remote_asset_bytes == 100 * 1024 * 1024
    assert settings.remote_download_timeout_seconds == 60
    assert settings.allow_private_network_downloads is False
    assert settings.allowed_remote_asset_schemes == ["https", "http"]


def test_settings_load_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
