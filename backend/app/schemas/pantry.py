from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class PantryItemCreate(BaseModel):
    ingredient_name: str = Field(..., min_length=1, description="Name of the ingredient to add")
    quantity: float = Field(..., gt=0.0, description="Quantity of the ingredient")
    unit: str = Field(..., min_length=1, description="Measurement unit (e.g., grams, pieces)")
    expiration_date: Optional[date] = Field(None, description="Optional expiration date")


class PantryItemUpdate(BaseModel):
    quantity: Optional[float] = Field(None, gt=0.0, description="Updated quantity")
    unit: Optional[str] = Field(None, min_length=1, description="Updated measurement unit")
    expiration_date: Optional[date] = Field(None, description="Updated expiration date")


class PantryItemRead(BaseModel):
    id: str
    ingredient_id: str
    ingredient_name: str
    canonical_name: str
    quantity: float
    unit: str
    expiration_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipeIngredientCheck(BaseModel):
    ingredient_name: str
    required_quantity: float
    required_unit: str
    pantry_quantity: float
    pantry_unit: str
    status: str = Field(..., description="'covered', 'partially_covered', or 'missing'")


class PantryRecipeCheckResponse(BaseModel):
    recipe_id: str
    recipe_name: str
    required_ingredients: List[RecipeIngredientCheck]
    pantry_covered: List[RecipeIngredientCheck]
    partially_covered: List[RecipeIngredientCheck]
    missing_ingredients: List[RecipeIngredientCheck]
