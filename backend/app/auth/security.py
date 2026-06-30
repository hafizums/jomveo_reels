import secrets

from starlette.requests import Request

from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError


def admin_token_from_request(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization is not None:
        scheme, separator, token = authorization.partition(" ")
        if separator and scheme.casefold() == "bearer" and token.strip():
            return token.strip()
        return None
    fallback = request.headers.get("X-Admin-API-Key", "").strip()
    return fallback or None


def is_valid_admin_key(candidate: str, configured_keys: list[str]) -> bool:
    matches = [secrets.compare_digest(candidate, configured) for configured in configured_keys]
    return any(matches)


def validate_admin_configuration(settings: Settings) -> None:
    if (
        settings.app_env.casefold() == "production"
        and settings.admin_auth_enabled
        and not settings.admin_api_keys
    ):
        raise ConfigurationError(
            "Production admin authentication requires at least one configured admin API key."
        )
