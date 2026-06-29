from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import ConfigurationError

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str | bool]:
    try:
        generated_root = settings.generated_root.expanduser().resolve()
        generated_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigurationError("Generated media directory is not available.") from exc
    return {
        "status": "ready",
        "environment": settings.app_env,
        "generated_root_exists": generated_root.is_dir(),
    }
