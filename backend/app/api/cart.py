"""
DishIQ Phase 7.4 — Cart Comparison & Optimization API Endpoints
  POST /api/cart/compare   — per-store basket breakdowns
  POST /api/cart/optimize  — recommended shopping strategy
"""
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any, Set
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
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


def _match_all_ingredients(
    request: CartCompareRequest,
    db: Session,
    live_mode: bool = False,
    background_tasks: Optional[BackgroundTasks] = None,
    per_ingredient_timeout: Optional[float] = None,
) -> Tuple[Dict[str, list], List[CartMissingIngredient]]:
    """
    For each ingredient in the cart request, run semantic product matching
    via the existing GroceryService pipeline (provider → matcher → price comparison).

    Optimizations:
    - Deduplicates identical or duplicate ingredient queries within the request.
    - Uses bounded concurrency (ThreadPoolExecutor) for independent ingredient searches.
    - Applies explicit per-provider request timeouts to guarantee responses finish
      well within the client's timeout budget.
    - Preserves stock checks and data provenance (never replaces live data with demo prices).
    """
    if not request.ingredients:
        return {}, []

    effective_timeout = (
        per_ingredient_timeout
        if per_ingredient_timeout is not None
        else getattr(settings, "GROCERY_SEARCH_TIMEOUT_SECONDS", 4.0)
    )

    # 1. Identify distinct non-empty ingredient queries to avoid redundant searches
    query_to_name: Dict[str, str] = {}
    for ing in request.ingredients:
        raw_name = (ing.ingredient_name or "").strip()
        if raw_name:
            key = raw_name.lower()
            if key not in query_to_name:
                query_to_name[key] = raw_name

    query_results: Dict[str, Tuple[list, Optional[str]]] = {}

    def _search_single(query_name: str) -> Tuple[str, list, Optional[str]]:
        try:
            service = GroceryService(db)
            response = service.match_products_for_ingredient(
                ingredient=query_name,
                limit=20,
                sort_by_price=True,
                live_mode=live_mode,
                background_tasks=background_tasks,
                timeout=effective_timeout,
            )
            return query_name, response.results, None
        except Exception as ex:
            err_msg = str(ex) if str(ex) else "Product matching failed for this ingredient"
            return query_name, [], err_msg

    # 2. Run searches with bounded concurrency for distinct queries
    if len(query_to_name) == 1:
        single_name = next(iter(query_to_name.values()))
        _, res, err = _search_single(single_name)
        query_results[single_name.lower()] = (res, err)
    elif len(query_to_name) > 1:
        max_concurrency = getattr(settings, "CART_OPTIMIZATION_CONCURRENCY", 4)
        workers = max(1, min(len(query_to_name), max_concurrency))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_key = {
                executor.submit(_search_single, name): key
                for key, name in query_to_name.items()
            }
            for future in concurrent.futures.as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    _, res, err = future.result()
                    query_results[key] = (res, err)
                except Exception as ex:
                    query_results[key] = ([], str(ex) or "Product matching failed for this ingredient")

    # 3. Populate matched_products_by_ingredient and global_missing for all ingredients in request
    matched_products_by_ingredient: Dict[str, list] = {}
    global_missing: List[CartMissingIngredient] = []
    seen_missing: Set[str] = set()

    for ing in request.ingredients:
        raw_name = (ing.ingredient_name or "").strip()
        if not raw_name:
            matched_products_by_ingredient[ing.ingredient_name] = []
            if ing.ingredient_name not in seen_missing:
                seen_missing.add(ing.ingredient_name)
                global_missing.append(
                    CartMissingIngredient(
                        ingredient_name=ing.ingredient_name,
                        reason="Ingredient query cannot be empty or whitespace-only",
                    )
                )
            continue

        key = raw_name.lower()
        results, err = query_results.get(key, ([], "Product matching failed for this ingredient"))
        matched_products_by_ingredient[ing.ingredient_name] = results
        if not results and err:
            if ing.ingredient_name not in seen_missing:
                seen_missing.add(ing.ingredient_name)
                reason_text = (
                    "Product matching timed out for this ingredient"
                    if "timeout" in err.lower()
                    else ("Product matching failed for this ingredient: " + err if len(err) < 60 else "Product matching failed for this ingredient")
                )
                global_missing.append(
                    CartMissingIngredient(
                        ingredient_name=ing.ingredient_name,
                        reason=reason_text,
                    )
                )

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
    background_tasks: BackgroundTasks,
    live_mode: bool = Query(False, description="Enable real-time live price fetching"),
    db: Session = Depends(get_db),
) -> CartCompareResponse:
    matched, global_missing = _match_all_ingredients(request, db, live_mode=live_mode, background_tasks=background_tasks)

    baskets = build_store_baskets(request.ingredients, matched)

    # Identify ingredients missing from ALL stores
    all_store_missing = set()
    for ing in request.ingredients:
        found_anywhere = False
        if baskets:
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

    freshness = "UNKNOWN"
    if matched:
        for p_list in matched.values():
            if p_list and hasattr(p_list[0], "price_freshness"):
                freshness = p_list[0].price_freshness
                break

    return CartCompareResponse(
        stores=baskets,
        missing_ingredients=combined_missing,
        data_source="live" if live_mode else "demo",
        price_freshness=freshness,
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
    background_tasks: BackgroundTasks,
    live_mode: bool = Query(False, description="Enable real-time live price fetching"),
    db: Session = Depends(get_db),
) -> CartOptimizeResponse:
    matched, global_missing = _match_all_ingredients(request, db, live_mode=live_mode, background_tasks=background_tasks)

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

    freshness = "UNKNOWN"
    if matched:
        for p_list in matched.values():
            if p_list and hasattr(p_list[0], "price_freshness"):
                freshness = p_list[0].price_freshness
                break

    if not candidates:
        # No complete strategy available ?" return best effort
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
            store_baskets=baskets,
            total_cost=0,
            estimated_savings=0,
            stores_used=0,
            missing_ingredients=all_missing,
            explanation="No complete shopping plan could be constructed from available products.",
            data_source="live" if live_mode else "demo",
            price_freshness=freshness,
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
        store_baskets=baskets,
        total_cost=recommended.total_cost,
        currency=recommended.currency,
        estimated_savings=savings,
        stores_used=recommended.stores_used,
        missing_ingredients=recommended.missing_ingredients,
        explanation=recommended.explanation,
        data_source="live" if live_mode else "demo",
        price_freshness=freshness,
    )
