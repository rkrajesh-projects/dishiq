"""
DishIQ Phase 9 — Shopping List Schemas
Pydantic request and response models for shopping lists, items, and grocery integration.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SourceRecipeInfo(BaseModel):
    recipe_id: str
    recipe_name: str
    quantity: float
    unit: str


class ShoppingListItemCreate(BaseModel):
    ingredient_name: str = Field(..., min_length=1, max_length=255, description="Ingredient display name")
    quantity: float = Field(..., gt=0, description="Quantity to buy")
    unit: str = Field(default="piece", min_length=1, max_length=50, description="Unit of measurement")
    notes: Optional[str] = None

    @field_validator("ingredient_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Ingredient name cannot be blank.")
        return s

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        s = v.strip().lower()
        if not s:
            return "piece"
        return s


class ShoppingListItemUpdate(BaseModel):
    is_obtained: Optional[bool] = None
    user_quantity_override: Optional[float] = Field(None, ge=0, description="Manual quantity override")
    notes: Optional[str] = None


class ShoppingListItemRead(BaseModel):
    id: str
    shopping_list_id: str
    ingredient_id: Optional[str] = None
    ingredient_name: str
    required_quantity: float
    unit: str
    pantry_quantity: float = 0.0
    quantity_to_buy: float = 0.0
    user_quantity_override: Optional[float] = None
    effective_quantity: float = 0.0
    is_obtained: bool = False
    is_manual: bool = False
    source_recipes: List[Any] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShoppingListGenerateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Custom name for the shopping list")
    deduct_pantry: bool = Field(default=True, description="Whether to deduct available pantry stock")


class ShoppingListCreate(BaseModel):
    name: str = Field(default="My Shopping List", min_length=1, max_length=255, description="Name for the shopping list")
    meal_plan_id: Optional[str] = Field(None, description="Optional associated meal plan ID")


class ShoppingListRead(BaseModel):
    id: str
    user_id: Optional[str] = None
    meal_plan_id: Optional[str] = None
    name: str
    status: str = "active"
    items: List[ShoppingListItemRead] = Field(default_factory=list)
    total_items: int = 0
    obtained_items: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShoppingListGroceryItemMatch(BaseModel):
    item_id: str
    ingredient_name: str
    quantity_needed: float
    unit: str
    matched_products: List[Dict[str, Any]] = Field(default_factory=list)
    best_product: Optional[Dict[str, Any]] = None
    missing_reason: Optional[str] = None


class ShoppingListGroceryComparisonResponse(BaseModel):
    shopping_list_id: str
    items: List[ShoppingListGroceryItemMatch] = Field(default_factory=list)
    store_baskets: List[Dict[str, Any]] = Field(default_factory=list)
    unmatched_ingredients: List[str] = Field(default_factory=list)
    total_estimated_cost: Optional[float] = None
    is_complete: bool = False
    notes: Optional[str] = None
