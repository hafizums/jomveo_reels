from pathlib import Path

import pytest
from pydantic import ValidationError

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
    assert settings.billing_enabled is True
    assert settings.demo_billing_enabled is False
    assert settings.default_project_starting_credits == 0
    assert settings.default_daily_job_limit == 100
    assert settings.default_monthly_job_limit == 1000
    assert settings.default_max_concurrent_jobs == 3
    assert settings.pricing_version == "2026-06-30"
    assert settings.provider_asset_retention_days == 7
    assert settings.provider_asset_expiring_soon_hours == 24
    assert settings.asset_download_warning_enabled is True
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
    assert settings.openai_api_key == ""
    assert settings.transcription_provider == "none"
    assert settings.transcription_model == "whisper-1"
    assert settings.transcription_output_format == "srt"
    assert settings.transcription_prompt == ""
    assert settings.transcription_timeout_seconds == 600


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


@pytest.mark.parametrize(
    ("field", "value"),
    [("transcription_provider", "local"), ("transcription_output_format", "json")],
)
def test_transcription_settings_reject_unsupported_values(field, value) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_blank_optional_limits_are_loaded_as_none(monkeypatch) -> None:
    monkeypatch.setenv("DEFAULT_DAILY_CREDIT_LIMIT", "")
    monkeypatch.setenv("DEFAULT_MONTHLY_CREDIT_LIMIT", "   ")

    settings = Settings(_env_file=None)

    assert settings.default_daily_credit_limit is None
    assert settings.default_monthly_credit_limit is None
