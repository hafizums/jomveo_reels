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
    wavespeed_api_key: str = ""
    wavespeed_llm_base_url: str = "https://llm.wavespeed.ai/v1"
    wavespeed_api_base_url: str = "https://api.wavespeed.ai/api/v3"
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    generated_root: Path = BACKEND_ROOT / "generated"
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

    @field_validator("generated_root")
    @classmethod
    def resolve_generated_root(cls, value: Path) -> Path:
        return value if value.is_absolute() else BACKEND_ROOT / value


@lru_cache
def get_settings() -> Settings:
    return Settings()
