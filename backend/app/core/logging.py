import json
import logging
import re
import sys
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.metrics import metrics

# Regex pattern matching sensitive query parameters and credential tokens (case-insensitive)
SENSITIVE_PARAM_PATTERN = re.compile(
    r"(?i)([\?&](?:code|state|token|access_token|refresh_token|client_secret|authorization|key|api_key|apiKey|password|secret)=)([^&\s\"'>#]+)"
)

# Safe pattern for incoming correlation IDs: alphanumeric, hyphen, underscore; 1 to 64 chars
SAFE_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def redact_sensitive_query_params(text: str) -> str:
    """
    Redact OAuth authorization codes, anti-CSRF state tokens, client secrets,
    API keys, passwords, and access/refresh tokens from URLs, query strings, and log messages.
    """
    if not isinstance(text, str):
        return text
    return SENSITIVE_PARAM_PATTERN.sub(r"\g<1>[REDACTED]", text)


def sanitize_log_text(text: str) -> str:
    """
    Redacts sensitive parameters and strips carriage return / linefeed characters
    to prevent CRLF log-injection / log forging attacks.
    """
    if not isinstance(text, str):
        return text
    redacted = redact_sensitive_query_params(text)
    return redacted.replace("\r", " ").replace("\n", " ")


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that sanitizes sensitive OAuth credentials, query parameters,
    and tokens across log records (both message templates and arguments).
    Also sanitizes newlines to prevent log injection.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_log_text(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_log_text(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: (sanitize_log_text(v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
        return True


class StructuredJSONFormatter(logging.Formatter):
    """
    JSON Formatter for structured logging across application events, requests, and errors.
    Automatically redacts sensitive parameters.
    """
    def format(self, record: logging.LogRecord) -> str:
        msg = sanitize_log_text(record.getMessage())
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": msg,
            "environment": settings.ENVIRONMENT,
            "app": settings.APP_NAME,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = getattr(record, "request_id")
        if hasattr(record, "http_method"):
            log_data["http_method"] = getattr(record, "http_method")
        if hasattr(record, "path"):
            log_data["path"] = sanitize_log_text(str(getattr(record, "path")))
        if hasattr(record, "status_code"):
            log_data["status_code"] = getattr(record, "status_code")
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = getattr(record, "duration_ms")

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """
    Configures application-wide structured logger with automatic redaction.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger = logging.getLogger("dishiq")
    logger.setLevel(log_level)
    logger.handlers.clear()

    sensitive_filter = SensitiveDataFilter()
    logger.addFilter(sensitive_filter)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter())
    handler.addFilter(sensitive_filter)
    logger.addHandler(handler)

    # Disable duplicate propagation
    logger.propagate = False

    # Also install redaction filter on uvicorn access and general loggers
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.addFilter(sensitive_filter)
        for h in uv_logger.handlers:
            h.addFilter(sensitive_filter)

    return logger


logger = setup_logging()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware capturing and logging HTTP request details, duration,
    request correlation IDs, defense-in-depth security headers, and metrics.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Correlation ID: validate incoming header or generate a safe unique ID
        incoming_id = request.headers.get("x-request-id", "").strip()
        if incoming_id and SAFE_REQUEST_ID_PATTERN.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = uuid.uuid4().hex

        request.state.request_id = request_id

        path = request.url.path
        raw_query = request.url.query
        sanitized_query = redact_sensitive_query_params(raw_query) if raw_query else ""
        method = request.method

        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)
        path_logged = f"{path}?{sanitized_query}" if sanitized_query else path
        
        # Attach correlation ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Attach standard defense-in-depth security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Record operational metrics
        metrics.record_request(method, response.status_code, duration_ms)

        extra = {
            "request_id": request_id,
            "http_method": method,
            "path": path_logged,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        
        logger.info(
            f"[{request_id}] HTTP {method} {path_logged} - {response.status_code} ({duration_ms}ms)",
            extra=extra
        )

        return response
