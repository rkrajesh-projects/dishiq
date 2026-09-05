from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.grocery_service import GroceryService
from app.schemas.grocery import GroceryProductRead
from app.schemas.pagination import PaginatedResponse
from app.product_matching.schemas import MatchIngredientsResponse

router = APIRouter(prefix="/products", tags=["Products & Grocery Matching"])


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
def match_ingredient_products(
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


@router.get("", response_model=PaginatedResponse[GroceryProductRead], summary="List Demonstration Grocery Products")
def get_products(
    store_id: Optional[str] = Query(None, description="Filter products by store ID"),
    category: Optional[str] = Query(None, description="Filter products by category (e.g. Dairy, Produce)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    db: Session = Depends(get_db),
):
    service = GroceryService(db)
    return service.list_products(store_id=store_id, category=category, page=page, page_size=page_size)
