from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "JomVeo Reels API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api"
    admin_auth_enabled: bool = True
    admin_api_keys: list[str] = Field(default_factory=list)
    user_auth_enabled: bool = False
    demo_user_enabled: bool = True
    demo_user_email: str = "demo@jomveo.local"
    billing_enabled: bool = True
    demo_billing_enabled: bool = False
    default_project_starting_credits: int = 0
    default_daily_job_limit: int | None = 100
    default_monthly_job_limit: int | None = 1000
    default_daily_credit_limit: int | None = None
    default_monthly_credit_limit: int | None = None
    default_max_concurrent_jobs: int | None = 3
    pricing_version: str = "2026-06-30"
    provider_asset_retention_days: int = 7
    provider_asset_expiring_soon_hours: int = 24
    asset_download_warning_enabled: bool = True
    wavespeed_api_key: str = ""
    wavespeed_llm_base_url: str = "https://llm.wavespeed.ai/v1"
    wavespeed_api_base_url: str = "https://api.wavespeed.ai/api/v3"
    wavespeed_provider_mode: str = "sdk"
    wavespeed_sdk_timeout_seconds: float = 36000.0
    wavespeed_sdk_poll_interval_seconds: float = 1.0
    wavespeed_sdk_enable_sync_mode: bool = False
    allow_provider_live_checks: bool = False
    provider_smoke_test_model: str = "wavespeed-ai/z-image/turbo"
    provider_smoke_test_timeout_seconds: float = 120.0
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    generated_root: Path = BACKEND_ROOT / "generated"
    storage_backend: str = "local"
    local_storage_root: Path = BACKEND_ROOT / "generated"
    public_generated_url_prefix: str = "/generated"
    max_upload_bytes: int = 100 * 1024 * 1024
    max_remote_asset_bytes: int = 100 * 1024 * 1024
    remote_download_timeout_seconds: int = 60
    allow_private_network_downloads: bool = False
    allowed_remote_asset_schemes: list[str] = Field(default_factory=lambda: ["https", "http"])
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    transcription_provider: str = Field(default="none", validation_alias="TRANSCRIPTION_PROVIDER")
    transcription_model: str = Field(default="whisper-1", validation_alias="TRANSCRIPTION_MODEL")
    transcription_output_format: str = Field(
        default="srt", validation_alias="TRANSCRIPTION_OUTPUT_FORMAT"
    )
    transcription_prompt: str = Field(default="", validation_alias="TRANSCRIPTION_PROMPT")
    transcription_timeout_seconds: int = Field(
        default=600, ge=1, validation_alias="TRANSCRIPTION_TIMEOUT_SECONDS"
    )
    database_url: str = "sqlite:///backend/generated/jomveo.db"
    queue_backend: str = "inline"
    redis_url: str = "redis://localhost:6379/0"
    job_default_timeout_seconds: int = 1800
    job_max_attempts: int = 3
    job_retry_backoff_seconds: int = 30
    job_stale_after_seconds: int = 900
    job_worker_id: str = "local-worker"
    log_level: str = "INFO"
    request_id_header: str = "X-Request-ID"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("debug", mode="before")
    @classmethod
    def tolerate_unrelated_debug_environment_values(cls, value: object) -> object:
        if isinstance(value, str) and value.casefold() not in {
            "0",
            "1",
            "false",
            "no",
            "off",
            "on",
            "true",
            "yes",
        }:
            return False
        return value

    @field_validator("generated_root", "local_storage_root")
    @classmethod
    def resolve_generated_root(cls, value: Path) -> Path:
        return value if value.is_absolute() else BACKEND_ROOT / value

    @field_validator("admin_api_keys")
    @classmethod
    def normalize_admin_api_keys(cls, value: list[str]) -> list[str]:
        return [key.strip() for key in value if key.strip()]

    @field_validator(
        "default_daily_job_limit",
        "default_monthly_job_limit",
        "default_daily_credit_limit",
        "default_monthly_credit_limit",
        "default_max_concurrent_jobs",
        mode="before",
    )
    @classmethod
    def blank_optional_limits_are_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("transcription_provider")
    @classmethod
    def validate_transcription_provider(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in {"none", "openai"}:
            raise ValueError("TRANSCRIPTION_PROVIDER must be 'none' or 'openai'.")
        return normalized

    @field_validator("transcription_output_format")
    @classmethod
    def validate_transcription_output_format(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in {"srt", "vtt"}:
            raise ValueError("TRANSCRIPTION_OUTPUT_FORMAT must be 'srt' or 'vtt'.")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
