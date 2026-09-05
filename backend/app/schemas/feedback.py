from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class RecipeFeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Recipe rating from 1 to 5")
    difficulty: str = Field("Medium", description="Recipe difficulty: Easy, Medium, Hard")
    notes: Optional[str] = Field(None, description="Optional text feedback notes")

class RecipeFeedbackRead(BaseModel):
    id: str
    user_id: str
    recipe_id: str
    rating: int
    difficulty: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
