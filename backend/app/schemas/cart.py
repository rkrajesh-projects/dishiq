"""
DishIQ Phase 7 — Cart Comparison & Optimization Schemas
Pydantic request/response models for multi-ingredient cart comparison
and shopping strategy optimization.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class CartIngredientRequest(BaseModel):
    """A single ingredient requirement for cart optimization."""
    ingredient_name: str = Field(
        ..., min_length=1, description="Ingredient name (e.g. 'paneer', 'tomato')"
    )
    required_quantity: float = Field(
        ..., gt=0, description="Required quantity (e.g. 500.0)"
    )
    required_unit: str = Field(
        ..., min_length=1, description="Unit of measurement (e.g. 'g', 'kg', 'ml', 'pieces')"
    )

    @field_validator("ingredient_name")
    @classmethod
    def validate_ingredient_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Ingredient name cannot be blank.")
        return stripped

    @field_validator("required_unit")
    @classmethod
    def validate_required_unit(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Required unit cannot be blank.")
        return stripped


class CartCompareRequest(BaseModel):
    """Request body for cart comparison and optimization endpoints."""
    ingredients: List[CartIngredientRequest] = Field(
        ..., min_length=1, max_length=50,
        description="List of required ingredients with quantities"
    )


class CartProductSelection(BaseModel):
    """A single product selected for a cart ingredient line."""
    ingredient_name: str = Field(..., description="Ingredient this product fulfills")
    product_id: str = Field(..., description="Matched grocery product ID")
    product_name: str = Field(..., description="Grocery product display name")
    store_id: Optional[str] = Field(None, description="Store ID")
    store_name: Optional[str] = Field(None, description="Store display name")
    brand: Optional[str] = Field(None, description="Product brand")
    package_quantity: Optional[float] = Field(None, description="Package size quantity")
    package_unit: Optional[str] = Field(None, description="Package size unit")
    packages_required: int = Field(..., ge=1, description="Number of packages needed")
    package_price: Optional[float] = Field(None, description="Price per package in INR")
    line_cost: float = Field(..., description="Total line cost (packages × price) in INR")
    currency: str = Field(default="INR", description="Currency code")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Semantic match similarity score")
    in_stock: bool = Field(default=True, description="Whether product is in stock")
    data_source_type: str = Field(default="demo", description="Data source identifier")
    price_freshness: str = Field(default="CACHED", description="Price freshness status")


class CartMissingIngredient(BaseModel):
    """An ingredient that could not be fulfilled by any store."""
    ingredient_name: str = Field(..., description="Ingredient name")
    reason: str = Field(..., description="Reason the ingredient is missing")


class CartStoreBreakdown(BaseModel):
    """Cost breakdown for a single store's contribution to a cart."""
    store_id: Optional[str] = Field(None, description="Store ID")
    store_name: str = Field(..., description="Store display name")
    selected_products: List[CartProductSelection] = Field(
        default_factory=list, description="Products selected from this store"
    )
    missing_ingredients: List[CartMissingIngredient] = Field(
        default_factory=list, description="Ingredients not available at this store"
    )
    subtotal: float = Field(default=0.0, description="Sum of line costs in INR")
    delivery_fee: float = Field(default=0.0, description="Delivery fee in INR")
    total: float = Field(default=0.0, description="Subtotal + delivery fee in INR")
    complete: bool = Field(
        default=False,
        description="True if all required ingredients are satisfied by this store"
    )


class CartCompareResponse(BaseModel):
    """Response for cart comparison showing per-store breakdowns."""
    stores: List[CartStoreBreakdown] = Field(
        default_factory=list, description="Per-store cost breakdowns"
    )
    missing_ingredients: List[CartMissingIngredient] = Field(
        default_factory=list, description="Ingredients missing from ALL stores"
    )
    data_source: str = Field(default="demo", description="Primary data source identifier")
    price_freshness: str = Field(default="CACHED", description="Price freshness status")


class CartStrategyResult(BaseModel):
    """Result of a single shopping strategy."""
    strategy: str = Field(..., description="Strategy identifier")
    stores: List[CartStoreBreakdown] = Field(
        default_factory=list, description="Store breakdowns for this strategy"
    )
    stores_used: int = Field(default=0, description="Number of stores used")
    total_cost: float = Field(default=0.0, description="Final total including delivery in INR")
    currency: str = Field(default="INR", description="Currency code")
    missing_ingredients: List[CartMissingIngredient] = Field(
        default_factory=list, description="Unfulfilled ingredients"
    )
    explanation: str = Field(default="", description="Human-readable strategy explanation")


class CartOptimizeResponse(BaseModel):
    """Response for cart optimization with recommended and alternative strategies."""
    recommended_strategy: str = Field(
        ..., description="Identifier of the recommended strategy"
    )
    recommended_cart: CartStrategyResult = Field(
        ..., description="Details of the recommended shopping plan"
    )
    alternatives: List[CartStrategyResult] = Field(
        default_factory=list, description="Alternative strategy results"
    )
    total_cost: float = Field(
        ..., description="Total cost of the recommended strategy in INR"
    )
    currency: str = Field(default="INR", description="Currency code")
    estimated_savings: float = Field(
        default=0.0, description="Estimated savings vs next-best alternative in INR"
    )
    stores_used: int = Field(default=0, description="Number of stores in recommended plan")
    missing_ingredients: List[CartMissingIngredient] = Field(
        default_factory=list, description="Ingredients not available anywhere"
    )
    explanation: str = Field(default="", description="Human-readable recommendation explanation")
    data_source: str = Field(default="demo", description="Primary data source identifier")
    price_freshness: str = Field(default="CACHED", description="Price freshness status")
