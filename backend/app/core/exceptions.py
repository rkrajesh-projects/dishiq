from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.logging import logger


class DishIQException(Exception):
    """
    Base exception class for DishIQ domain errors.
    """
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


def format_error_response(code: str, message: str, details: Optional[Any] = None) -> Dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers global exception handlers on the FastAPI application instance.
    """

    @app.exception_handler(DishIQException)
    async def dishiq_exception_handler(request: Request, exc: DishIQException) -> JSONResponse:
        logger.error(f"DishIQException: {exc.message}", extra={"code": exc.code, "path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.warning(f"HTTPException {exc.status_code}: {exc.detail}", extra={"path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(
                code=f"HTTP_{exc.status_code}",
                message=str(exc.detail),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"RequestValidationError on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=format_error_response(
                code="VALIDATION_ERROR",
                message="Request payload or parameters validation failed.",
                details=exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True, extra={"path": request.url.path})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=format_error_response(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred.",
            ),
        )
