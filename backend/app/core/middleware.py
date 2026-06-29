import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.app.core.logging import bind_request_id, reset_request_id

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, request_id_header: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.request_id_header = request_id_header

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        supplied_id = request.headers.get(self.request_id_header, "").strip()
        request_id = (
            supplied_id[:128] if supplied_id and supplied_id.isprintable() else str(uuid.uuid4())
        )
        request.state.request_id = request_id
        token = bind_request_id(request_id)
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[self.request_id_header] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            reset_request_id(token)
