import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, status, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import metrics
from app.db.session import get_db
from app.core.logging import logger

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    application: str
    version: str
    checks: Dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Liveness Check",
    description="Confirms the application process is running and responding to requests.",
)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        application=settings.APP_NAME,
        version=settings.APP_VERSION,
    )


@router.get(
    "/health/liveness",
    response_model=HealthResponse,
    summary="Application Liveness Probe",
    description="Kubernetes/Docker liveness probe indicating process is active.",
)
async def get_liveness() -> HealthResponse:
    return HealthResponse(
        status="ok",
        application=settings.APP_NAME,
        version=settings.APP_VERSION,
    )


@router.get(
    "/health/readiness",
    response_model=ReadinessResponse,
    summary="Application Readiness Probe",
    description="Verifies database connectivity and essential components without exposing credentials.",
)
def get_readiness(response: Response, db: Session = Depends(get_db)) -> ReadinessResponse:
    checks = {
        "database": "unknown",
        "models": "ready",
    }

    is_ready = True

    # 1. Database connectivity check with strict 2-second statement timeout
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as db_err:
        logger.error(f"Readiness check database failure: {db_err}")
        metrics.record_db_error()
        checks["database"] = "unreachable"
        is_ready = False

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="unhealthy",
            application=settings.APP_NAME,
            version=settings.APP_VERSION,
            checks=checks,
        )

    return ReadinessResponse(
        status="ready",
        application=settings.APP_NAME,
        version=settings.APP_VERSION,
        checks=checks,
    )


@router.get(
    "/health/metrics",
    summary="Operational Metrics",
    description="Returns bounded, in-memory operational metrics for request traffic, error rates, and latencies.",
)
async def get_operational_metrics() -> Dict[str, Any]:
    return metrics.get_metrics()
