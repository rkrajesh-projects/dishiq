from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CookingSessionCreate(BaseModel):
    recipe_id: str = Field(..., min_length=1)
    notes: Optional[str] = None
    servings: Optional[int] = Field(None, gt=0)


class CookingSessionUpdate(BaseModel):
    current_step: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None
    notes: Optional[str] = None
    servings: Optional[int] = Field(None, gt=0)
    prepared_ingredients: Optional[List[str]] = None
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


class PreparedIngredientsUpdate(BaseModel):
    prepared_ingredients: List[str] = Field(default_factory=list)


class PreparationItem(BaseModel):
    id: str
    ingredient_id: Optional[str] = None
    name: str
    raw_text: str
    quantity: Optional[float] = None
    scaled_quantity: Optional[float] = None
    unit: Optional[str] = None
    preparation_note: Optional[str] = None
    category: Optional[str] = None
    is_prepared: bool = False
    to_taste: bool = False


class PreparationChecklistResponse(BaseModel):
    session_id: str
    recipe_id: str
    recipe_name: str
    servings: int
    base_servings: int
    scale_factor: float
    total_ingredients: int
    prepared_count: int
    all_prepared: bool
    items: List[PreparationItem]


class CookingSessionResponse(BaseModel):
    id: str
    user_id: str
    recipe_id: str
    current_step: int
    status: str
    started_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    servings: Optional[int] = None
    prepared_ingredients: Optional[List[str]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
