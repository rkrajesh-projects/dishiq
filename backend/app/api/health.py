from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Check",
    description="Returns application health status. Does not depend on external database services.",
)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        application=settings.APP_NAME,
        version=settings.APP_VERSION,
    )
