"""
DishIQ Phase 6.1 & 6.3 — Grocery Product Matching & Price Comparison
Pydantic schemas for semantic grocery product matching and price comparison.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class BestProductOption(BaseModel):
    """
    Identifies the single best/cheapest suitable grocery product option.
    """
    product_id: str = Field(..., description="Unique product ID")
    product_name: str = Field(..., description="Full grocery product display name")
    store_id: Optional[str] = Field(None, description="Store ID where product is sold")
    store_name: Optional[str] = Field(None, description="Store display name")
    brand: Optional[str] = Field(None, description="Product brand name")
    category: Optional[str] = Field(None, description="Product category")
    price: float = Field(..., description="Package price in INR (₹)")
    currency: str = Field(default="INR", description="Currency code (always INR)")
    package_quantity: Optional[float] = Field(None, description="Package quantity (e.g. 200.0)")
    package_unit: Optional[str] = Field(None, description="Package unit (e.g. grams, kg, ml)")
    unit_price: Optional[float] = Field(None, description="Calculated unit price in INR per base unit")
    base_unit: Optional[str] = Field(None, description="Normalized base unit (e.g. g, ml, piece)")
    similarity_score: float = Field(..., description="Semantic similarity score")


class ProductMatchResult(BaseModel):
    """
    Typed result structure representing a single grocery product match with price comparison metadata.
    """
    product_id: str = Field(..., description="Unique grocery product ID")
    product_name: str = Field(..., description="Full grocery product display name")
    brand: Optional[str] = Field(None, description="Product brand name")
    category: Optional[str] = Field(None, description="Product category")
    store_id: Optional[str] = Field(None, description="Store ID where product is sold")
    store_name: Optional[str] = Field(None, description="Store display name")
    price: Optional[float] = Field(None, description="Current package price in INR (₹)")
    currency: str = Field(default="INR", description="Currency code (always INR)")
    package_quantity: Optional[float] = Field(None, description="Package quantity (e.g. 200.0)")
    package_unit: Optional[str] = Field(None, description="Package unit (e.g. grams, kg, ml)")
    unit_price: Optional[float] = Field(None, description="Calculated unit price in INR per base unit")
    base_unit: Optional[str] = Field(None, description="Normalized base unit (e.g. g, ml, piece)")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score in [0.0, 1.0]")
    matched_text: str = Field(..., description="Text string used for similarity encoding")
    match_status: str = Field(..., description="'matched' if similarity_score >= threshold else 'low_confidence'")
    rank: int = Field(..., ge=1, description="1-indexed rank position sorted descending by similarity")
    price_rank: Optional[int] = Field(None, ge=1, description="1-indexed rank position sorted ascending by price")


class MatchIngredientsRequest(BaseModel):
    """
    Request model for ingredient-to-product matching.
    """
    ingredient_name: str = Field(..., min_length=1, description="Raw or normalized ingredient text to match")
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional override for similarity threshold")
    top_k: Optional[int] = Field(10, ge=1, description="Maximum number of ranked product matches to return")


class MatchIngredientsResponse(BaseModel):
    """
    Response model containing ordered grocery product matches and price comparison metadata.
    """
    ingredient_text: str = Field(..., description="Original query ingredient string")
    canonical_name: str = Field(..., description="Phase 5.2 normalized canonical ingredient name")
    threshold: float = Field(..., description="Similarity threshold applied for match status")
    total_matches: int = Field(..., description="Total count of products matching above threshold")
    results: List[ProductMatchResult] = Field(..., description="Ranked list of product match results")
    best_option: Optional[BestProductOption] = Field(None, description="Cheapest suitable grocery product option")
    comparison_mode: Optional[str] = Field(None, description="Comparison mode used ('unit_price' or 'package_price')")


class GroceryCompareResponse(MatchIngredientsResponse):
    """
    Dedicated response model for price comparison queries.
    """
    pass
