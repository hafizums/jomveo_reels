import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.core.config import Settings
from backend.app.core.errors import AppError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_response(
    request: Request,
    settings: Settings,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
        headers={settings.request_id_header: request_id},
    )


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "application_error",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
            },
        )
        return _error_response(request, settings, exc.status_code, exc.code, exc.message)

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail: Any = exc.detail
        message = detail if isinstance(detail, str) else "HTTP request failed."
        return _error_response(request, settings, exc.status_code, "http_error", message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        message = "Request validation failed."
        if settings.debug and exc.errors():
            first_error = exc.errors()[0]
            location = ".".join(str(part) for part in first_error.get("loc", ()))
            message = f"{location}: {first_error.get('msg', message)}"
        return _error_response(request, settings, 422, "request_validation_error", message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", extra={"path": request.url.path})
        message = str(exc) if settings.debug else "An unexpected internal error occurred."
        return _error_response(request, settings, 500, "internal_server_error", message)
