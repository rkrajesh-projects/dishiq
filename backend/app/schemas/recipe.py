from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


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


class RecipeDetailRead(RecipeRead):
    instructions: List[str]
    source_url: Optional[str] = None
    ingredients: List[RecipeIngredientRead]

    model_config = ConfigDict(from_attributes=True)
