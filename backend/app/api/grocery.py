"""
DishIQ Phase 6.2 & 6.3 — Grocery API Integration & Price Comparison
API endpoints:
  GET /api/grocery/match
  GET /api/grocery/compare
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.grocery_service import GroceryService
from app.product_matching.schemas import MatchIngredientsResponse, GroceryCompareResponse

router = APIRouter(prefix="/grocery", tags=["Grocery Matching & Price Comparison"])


@router.get(
    "/match",
    response_model=MatchIngredientsResponse,
    summary="Match Ingredient to Grocery Products",
    description=(
        "Converts a raw or normalized ingredient string into a 384-dimensional "
        "embedding using all-MiniLM-L6-v2, compares it against the grocery product catalog "
        "via cosine similarity, and returns ranked products above the threshold."
    ),
)
def match_grocery_products(
    ingredient: str = Query(..., min_length=1, description="Ingredient string to match (e.g. 'paneer', '2 tomatoes')"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of ranked matches to return"),
    threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="Optional override for similarity score threshold"),
    db: Session = Depends(get_db),
) -> MatchIngredientsResponse:
    if not ingredient or not ingredient.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ingredient query parameter cannot be empty or whitespace-only."
        )
    service = GroceryService(db)
    return service.match_products_for_ingredient(ingredient=ingredient, limit=limit, threshold=threshold)


@router.get(
    "/compare",
    response_model=GroceryCompareResponse,
    summary="Compare Grocery Product Prices for an Ingredient",
    description=(
        "Semantically matches an ingredient to grocery products, calculates normalized unit prices "
        "in INR (₹), ranks products by price ascending, and identifies the cheapest/best shopping option."
    ),
)
def compare_grocery_prices(
    ingredient: str = Query(..., min_length=1, description="Ingredient string to compare (e.g. 'paneer', '2 tomatoes')"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of products to return"),
    threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="Optional override for similarity score threshold"),
    db: Session = Depends(get_db),
) -> GroceryCompareResponse:
    if not ingredient or not ingredient.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ingredient query parameter cannot be empty or whitespace-only."
        )
    service = GroceryService(db)
    return service.compare_grocery_prices(ingredient=ingredient, limit=limit, threshold=threshold)
