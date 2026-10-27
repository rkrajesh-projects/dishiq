from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class PantryItemCreate(BaseModel):
    ingredient_name: str = Field(..., min_length=1, description="Name of the ingredient to add")
    quantity: float = Field(..., gt=0.0, description="Quantity of the ingredient")
    unit: str = Field(..., min_length=1, description="Measurement unit (e.g., grams, pieces)")
    expiration_date: Optional[date] = Field(None, description="Optional expiration date")
    custom_name: Optional[str] = Field(None, description="Optional user custom display name")
    location: Optional[str] = Field(None, description="Storage location (e.g., Fridge, Freezer, Pantry)")
    notes: Optional[str] = Field(None, description="Optional user notes")


class PantryItemUpdate(BaseModel):
    quantity: Optional[float] = Field(None, gt=0.0, description="Updated quantity")
    unit: Optional[str] = Field(None, min_length=1, description="Updated measurement unit")
    expiration_date: Optional[date] = Field(None, description="Updated expiration date")
    custom_name: Optional[str] = Field(None, description="Updated custom display name")
    location: Optional[str] = Field(None, description="Updated storage location")
    notes: Optional[str] = Field(None, description="Updated notes")


class PantryItemRead(BaseModel):
    id: str
    ingredient_id: str
    ingredient_name: str
    canonical_name: str
    quantity: float
    unit: str
    expiration_date: Optional[date]
    custom_name: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
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


class ConsumptionPreviewItem(BaseModel):
    ingredient_id: Optional[str] = None
    ingredient_name: str
    required_quantity: float
    required_unit: str
    pantry_item_id: Optional[str] = None
    pantry_quantity: float = 0.0
    pantry_unit: Optional[str] = None
    converted_deduct_quantity: float = 0.0
    remaining_stock: float = 0.0
    is_compatible: bool = False
    can_deduct: bool = False
    status: str
    reason: Optional[str] = None


class ConsumptionPreviewRequest(BaseModel):
    recipe_id: Optional[str] = None
    cooking_session_id: Optional[str] = None
    servings: Optional[int] = None
    items: Optional[List[dict]] = None


class ConsumptionPreviewResponse(BaseModel):
    preview_token: str
    recipe_id: Optional[str] = None
    cooking_session_id: Optional[str] = None
    items: List[ConsumptionPreviewItem]
    total_deductible_items: int
    has_incompatible_or_uncertain: bool


class ConsumptionDeductionItem(BaseModel):
    pantry_item_id: str
    deduct_quantity: float = Field(..., gt=0.0)


class ConsumptionConfirmRequest(BaseModel):
    preview_token: str
    recipe_id: Optional[str] = None
    cooking_session_id: Optional[str] = None
    items: List[ConsumptionDeductionItem]


class ConsumptionConfirmResponse(BaseModel):
    success: bool
    deducted_count: int
    message: str
    deductions: List[dict]
