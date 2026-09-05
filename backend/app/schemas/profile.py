from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

class ProfilePreferenceRead(BaseModel):
    dietary_type: str = Field(..., description="Dietary preference: None, Vegetarian, Vegan, etc.")
    weekly_budget: float = Field(..., description="Weekly grocery budget in INR")
    household_size: int = Field(..., description="Number of household servings")
    disliked_ingredients: List[str] = Field(default=[], description="Ingredients the user dislikes")

    model_config = ConfigDict(from_attributes=True)

class ProfileRead(BaseModel):
    id: str
    email: str
    full_name: str
    preference: ProfilePreferenceRead

    model_config = ConfigDict(from_attributes=True)

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, description="Updated full name of the user")
    dietary_type: Optional[str] = Field(None, description="Updated dietary preference")
    weekly_budget: Optional[float] = Field(None, gt=0.0, description="Updated weekly budget")
    household_size: Optional[int] = Field(None, ge=1, description="Updated household size")
