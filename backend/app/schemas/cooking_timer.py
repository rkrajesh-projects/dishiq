from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CookingTimerCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=255, description="Descriptive label for the timer or step")
    duration_seconds: int = Field(..., gt=0, le=86400, description="Duration in seconds (1s to 24h)")
    step_index: Optional[int] = Field(None, ge=0, description="Associated recipe step index (0-based)")
    cooking_session_id: Optional[str] = Field(None, description="Associated cooking session ID")
    recipe_id: Optional[str] = Field(None, description="Associated recipe ID")
    auto_start: bool = Field(False, description="Immediately start the timer upon creation")


class CookingTimerUpdate(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=255)
    duration_seconds: Optional[int] = Field(None, gt=0, le=86400)


class CookingTimerResponse(BaseModel):
    id: str
    user_id: str
    cooking_session_id: Optional[str] = None
    recipe_id: Optional[str] = None
    step_index: Optional[int] = None
    label: str
    duration_seconds: int
    remaining_seconds: float
    status: str
    started_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
