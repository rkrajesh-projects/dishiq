"""
DishIQ Phase 14 — Security & Abuse Protection Middleware
"""

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from app.core.exceptions import format_error_response
from app.core.logging import logger

# 5 MB default maximum request body size
MAX_BODY_SIZE_BYTES = 5 * 1024 * 1024


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Guards the application against abusive, memory-exhausting oversized payloads.
    Rejects requests with Content-Length exceeding max_bytes with HTTP 413 Payload Too Large.
    """
    def __init__(self, app, max_bytes: int = MAX_BODY_SIZE_BYTES):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    logger.warning(
                        f"Request rejected: Content-Length {length} exceeds maximum allowed {self.max_bytes} bytes on {request.url.path}"
                    )
                    return JSONResponse(
                        status_code=413,
                        content=format_error_response(
                            code="PAYLOAD_TOO_LARGE",
                            message=f"Request payload exceeds the maximum allowed limit of {self.max_bytes // (1024 * 1024)}MB.",
                        ),
                    )
            except ValueError:
                pass

        return await call_next(request)
