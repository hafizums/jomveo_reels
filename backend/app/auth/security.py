import secrets

from starlette.requests import Request

from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError

DEFAULT_ADMIN_KEY = "change-me-dev-admin-key"


def credential_from_request(request: Request) -> tuple[str, str] | None:
    authorization = request.headers.get("Authorization")
    if authorization is not None:
        scheme, separator, token = authorization.partition(" ")
        if separator and scheme.casefold() == "bearer" and token.strip():
            return token.strip(), "bearer"
        return None
    admin_fallback = request.headers.get("X-Admin-API-Key", "").strip()
    if admin_fallback:
        return admin_fallback, "admin"
    user_fallback = request.headers.get("X-User-API-Key", "").strip()
    if user_fallback:
        return user_fallback, "user"
    return None


def admin_token_from_request(request: Request) -> str | None:
    credential = credential_from_request(request)
    if credential is None or credential[1] == "user":
        return None
    return credential[0]


def is_valid_admin_key(candidate: str, configured_keys: list[str]) -> bool:
    matches = [secrets.compare_digest(candidate, configured) for configured in configured_keys]
    return any(matches)


def validate_admin_configuration(settings: Settings) -> None:
    if settings.app_env.casefold() != "production":
        return
    if not settings.admin_auth_enabled:
        raise ConfigurationError("Production admin authentication cannot be disabled.")
    if not settings.admin_api_keys:
        raise ConfigurationError(
            "Production admin authentication requires at least one configured admin API key."
        )
    if DEFAULT_ADMIN_KEY in settings.admin_api_keys:
        raise ConfigurationError(
            "The default development admin API key is not allowed in production."
        )
