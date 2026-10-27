from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class IngredientRead(BaseModel):
    id: str
    canonical_name: str
    category: str
    default_unit: str

    model_config = ConfigDict(from_attributes=True)


class RecipeIngredientRead(BaseModel):
    id: str
    ingredient: IngredientRead
    raw_text: str
    quantity: float
    unit: str
    preparation_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RecipeRead(BaseModel):
    id: str
    name: str
    description: str
    cuisine: str
    dietary_type: str
    preparation_minutes: int
    cooking_minutes: int
    servings: int
    source_name: str
    average_rating: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipeStepRead(BaseModel):
    step_number: int
    text: str
    action_type: str
    timing_minutes: Optional[int] = None
    temperature: Optional[str] = None
    equipment: List[str] = []
    ingredients: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class RecipeDetailRead(RecipeRead):
    instructions: List[str] = Field(validation_alias="legacy_instructions")
    structured_instructions: Optional[List[RecipeStepRead]] = Field(None, validation_alias="structured_instructions_data")
    source_url: Optional[str] = None
    author: Optional[str] = None
    source_license: Optional[str] = None
    region: Optional[str] = None
    state: Optional[str] = None
    original_name: Optional[str] = None
    is_indian_recipe: Optional[bool] = None
    verification_status: Optional[str] = None
    ingredients: List[RecipeIngredientRead]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
