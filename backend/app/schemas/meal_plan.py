"""
DishIQ Phase 9 — Meal Planning Schemas
Pydantic request and response models for meal plan management.
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class MealPlanItemCreate(BaseModel):
    recipe_id: str = Field(..., min_length=1, description="Recipe identifier")
    meal_date: Optional[date] = Field(None, description="Planned date for the meal")
    meal_type: str = Field(default="dinner", description="Meal type: breakfast, lunch, dinner, snack")
    servings: int = Field(default=2, gt=0, description="Planned number of servings")
    notes: Optional[str] = Field(None, description="Optional notes or customization")

    @field_validator("recipe_id")
    @classmethod
    def validate_recipe_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("recipe_id cannot be blank.")
        return s

    @field_validator("meal_type")
    @classmethod
    def validate_meal_type(cls, v: str) -> str:
        s = v.strip().lower()
        if not s:
            return "dinner"
        return s


class MealPlanItemUpdate(BaseModel):
    meal_date: Optional[date] = None
    meal_type: Optional[str] = None
    servings: Optional[int] = Field(None, gt=0, description="Updated serving count")
    notes: Optional[str] = None

    @field_validator("meal_type")
    @classmethod
    def validate_meal_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip().lower()
            return s if s else "dinner"
        return v


class MealPlanItemRead(BaseModel):
    id: str
    meal_plan_id: str
    recipe_id: str
    recipe_name: str
    recipe_cuisine: Optional[str] = None
    meal_date: Optional[date] = None
    meal_type: str = "dinner"
    servings: int = 2
    original_servings: int = 4
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MealPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the meal plan")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    meals: Optional[List[MealPlanItemCreate]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Meal plan name cannot be blank.")
        return s


class MealPlanUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Meal plan name cannot be blank.")
            return s
        return v


class MealPlanRead(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    meals: List[MealPlanItemRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
