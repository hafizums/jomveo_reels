from pathlib import Path

from backend.app.core.config import Settings


def test_settings_have_local_development_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "JomVeo Reels API"
    assert settings.api_v1_prefix == "/api"
    assert settings.admin_auth_enabled is True
    assert settings.admin_api_keys == []
    assert settings.user_auth_enabled is False
    assert settings.demo_user_enabled is True
    assert settings.demo_user_email == "demo@jomveo.local"
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
    assert settings.wavespeed_provider_mode == "sdk"
    assert settings.wavespeed_sdk_timeout_seconds == 36000
    assert settings.wavespeed_sdk_poll_interval_seconds == 1
    assert settings.wavespeed_sdk_enable_sync_mode is False
    assert settings.allow_provider_live_checks is False
    assert settings.provider_smoke_test_model == "wavespeed-ai/z-image/turbo"
    assert settings.provider_smoke_test_timeout_seconds == 120


def test_settings_load_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ADMIN_AUTH_ENABLED", "true")
    monkeypatch.setenv("ADMIN_API_KEYS", '["first-admin-key", " second-admin-key "]')

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.admin_auth_enabled is True
    assert settings.admin_api_keys == ["first-admin-key", "second-admin-key"]
