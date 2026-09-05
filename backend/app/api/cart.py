"""
DishIQ Phase 7.4 — Cart Comparison & Optimization API Endpoints
  POST /api/cart/compare   — per-store basket breakdowns
  POST /api/cart/optimize  — recommended shopping strategy
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.grocery_service import GroceryService
from app.services.cart_optimization_service import (
    build_store_baskets,
    strategy_cheapest_single_store,
    strategy_cheapest_split_cart,
    strategy_fastest_available,
)
from app.schemas.cart import (
    CartCompareRequest,
    CartCompareResponse,
    CartOptimizeResponse,
    CartMissingIngredient,
)
from app.core.config import settings

router = APIRouter(prefix="/cart", tags=["Cart Comparison & Optimization"])


def _match_all_ingredients(request: CartCompareRequest, db: Session):
    """
    For each ingredient in the cart request, run semantic product matching
    via the existing GroceryService pipeline (provider → matcher → price comparison).

    Returns:
        matched_products_by_ingredient: dict mapping ingredient_name → list[ProductMatchResult]
        global_missing: list of CartMissingIngredient for ingredients with zero matches
    """
    service = GroceryService(db)
    matched_products_by_ingredient = {}
    global_missing = []

    for ing in request.ingredients:
        try:
            response = service.match_products_for_ingredient(
                ingredient=ing.ingredient_name,
                limit=20,
                sort_by_price=True,
            )
            matched_products_by_ingredient[ing.ingredient_name] = response.results
        except Exception:
            matched_products_by_ingredient[ing.ingredient_name] = []
            global_missing.append(CartMissingIngredient(
                ingredient_name=ing.ingredient_name,
                reason="Product matching failed for this ingredient"
            ))

    return matched_products_by_ingredient, global_missing


@router.post(
    "/compare",
    response_model=CartCompareResponse,
    summary="Compare Cart Across Stores",
    description=(
        "Takes a list of recipe ingredients with required quantities, "
        "matches each against the grocery catalog, and returns per-store "
        "basket breakdowns including package counts, line costs, delivery fees, and totals."
    ),
)
def compare_cart(
    request: CartCompareRequest,
    db: Session = Depends(get_db),
) -> CartCompareResponse:
    matched, global_missing = _match_all_ingredients(request, db)

    baskets = build_store_baskets(request.ingredients, matched)

    # Identify ingredients missing from ALL stores
    all_store_missing = set()
    if baskets:
        for ing in request.ingredients:
            found_anywhere = any(
                any(sel.ingredient_name == ing.ingredient_name for sel in b.selected_products)
                for b in baskets
            )
            if not found_anywhere:
                all_store_missing.add(ing.ingredient_name)

    combined_missing = list(global_missing)
    for name in all_store_missing:
        if not any(m.ingredient_name == name for m in combined_missing):
            combined_missing.append(CartMissingIngredient(
                ingredient_name=name,
                reason="No compatible in-stock product found at any store"
            ))

    return CartCompareResponse(
        stores=baskets,
        missing_ingredients=combined_missing,
        data_source="demo",
        price_freshness="CACHED",
    )


@router.post(
    "/optimize",
    response_model=CartOptimizeResponse,
    summary="Optimize Shopping Cart",
    description=(
        "Takes a list of recipe ingredients, evaluates three shopping strategies "
        "(cheapest single store, cheapest split cart, fastest available), "
        "and recommends the most practical shopping plan."
    ),
)
def optimize_cart(
    request: CartCompareRequest,
    db: Session = Depends(get_db),
) -> CartOptimizeResponse:
    matched, global_missing = _match_all_ingredients(request, db)

    baskets = build_store_baskets(request.ingredients, matched)

    # Strategy 1: Cheapest Single Store
    single_store = strategy_cheapest_single_store(baskets)

    # Strategy 2: Cheapest Split Cart
    split_cart = strategy_cheapest_split_cart(
        ingredients=request.ingredients,
        matched_products_by_ingredient=matched,
        max_stores=settings.CART_MAX_STORES,
        min_split_saving=settings.CART_MIN_SPLIT_SAVING,
        single_store_total=single_store.total_cost if single_store else None,
    )

    # Strategy 3: Fastest Available
    fastest = strategy_fastest_available(baskets)

    # Select recommended strategy
    candidates = []
    if split_cart:
        candidates.append(split_cart)
    if single_store:
        candidates.append(single_store)
    if fastest:
        candidates.append(fastest)

    if not candidates:
        # No complete strategy available — return best effort
        all_missing = list(global_missing)
        for ing in request.ingredients:
            if not any(m.ingredient_name == ing.ingredient_name for m in all_missing):
                found = any(
                    any(sel.ingredient_name == ing.ingredient_name for sel in b.selected_products)
                    for b in baskets
                )
                if not found:
                    all_missing.append(CartMissingIngredient(
                        ingredient_name=ing.ingredient_name,
                        reason="No compatible in-stock product found at any store"
                    ))

        from app.schemas.cart import CartStrategyResult
        empty_result = CartStrategyResult(
            strategy="none_available",
            stores=[],
            stores_used=0,
            total_cost=0,
            missing_ingredients=all_missing,
            explanation="No complete shopping plan could be constructed from available products.",
        )
        return CartOptimizeResponse(
            recommended_strategy="none_available",
            recommended_cart=empty_result,
            alternatives=[],
            total_cost=0,
            estimated_savings=0,
            stores_used=0,
            missing_ingredients=all_missing,
            explanation="No complete shopping plan could be constructed from available products.",
            data_source="demo",
            price_freshness="CACHED",
        )

    # Recommended = first candidate (cheapest split if available, else cheapest single)
    recommended = candidates[0]
    alternatives = candidates[1:]

    # Calculate savings vs next best
    savings = 0.0
    if len(candidates) >= 2:
        savings = round(candidates[1].total_cost - recommended.total_cost, 2)
        if savings < 0:
            savings = 0.0

    return CartOptimizeResponse(
        recommended_strategy=recommended.strategy,
        recommended_cart=recommended,
        alternatives=alternatives,
        total_cost=recommended.total_cost,
        estimated_savings=savings,
        stores_used=recommended.stores_used,
        missing_ingredients=recommended.missing_ingredients,
        explanation=recommended.explanation,
        data_source="demo",
        price_freshness="CACHED",
    )
