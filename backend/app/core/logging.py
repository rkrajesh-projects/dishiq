import json
import logging
import sys
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings


class StructuredJSONFormatter(logging.Formatter):
    """
    JSON Formatter for structured logging across application events, requests, and errors.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.ENVIRONMENT,
            "app": settings.APP_NAME,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = getattr(record, "request_id")
        if hasattr(record, "http_method"):
            log_data["http_method"] = getattr(record, "http_method")
        if hasattr(record, "path"):
            log_data["path"] = getattr(record, "path")
        if hasattr(record, "status_code"):
            log_data["status_code"] = getattr(record, "status_code")
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = getattr(record, "duration_ms")

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """
    Configures application-wide structured logger.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger = logging.getLogger("dishiq")
    logger.setLevel(log_level)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter())
    logger.addHandler(handler)

    # Disable duplicate propagation
    logger.propagate = False
    return logger


logger = setup_logging()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware capturing and logging HTTP request details and duration.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        path = request.url.path
        method = request.method

        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        extra = {
            "http_method": method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        
        logger.info(
            f"HTTP {method} {path} - {response.status_code} ({duration_ms}ms)",
            extra=extra
        )

        return response
