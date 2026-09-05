from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CookingSessionCreate(BaseModel):
    recipe_id: str = Field(..., min_length=1)
    notes: Optional[str] = None


class CookingSessionUpdate(BaseModel):
    current_step: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip().lower()
            if v_clean not in ("active", "paused", "completed"):
                raise ValueError("status must be 'active', 'paused', or 'completed'")
            return v_clean
        return v


class CookingSessionResponse(BaseModel):
    id: str
    user_id: str
    recipe_id: str
    current_step: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
