"""
DishIQ Phase 7 — Cart Optimization Service
Business logic for multi-ingredient cart comparison and shopping strategy optimization.

Reuses existing:
  - unit_pricing.normalize_unit_and_quantity() for unit conversion
  - ProductMatchResult schema for matched product data
  - PriceComparisonService for per-ingredient best_option (not duplicated)
  - Settings for configurable thresholds
"""
import math
from typing import List, Dict, Optional, Tuple
from itertools import combinations

from app.core.config import settings
from app.product_matching.unit_pricing import normalize_unit_and_quantity, calculate_unit_price, convert_cross_dimension_quantity
from app.product_matching.schemas import ProductMatchResult
from app.schemas.cart import (
    CartIngredientRequest,
    CartProductSelection,
    CartStoreBreakdown,
    CartMissingIngredient,
    CartStrategyResult,
)


def calculate_packages_required(
    required_qty: Optional[float],
    required_unit: Optional[str],
    package_qty: Optional[float],
    package_unit: Optional[str],
    ingredient_name: Optional[str] = None,
) -> Optional[int]:
    """
    Calculate the number of packages needed to satisfy a required quantity.

    Uses unit_pricing.normalize_unit_and_quantity() for base unit conversion,
    and convert_cross_dimension_quantity() for physical heuristics (piece-weight, density)
    when ingredient units and package units span different dimensions (e.g. pieces -> grams, tsp -> grams).

    Returns:
        Number of packages (>= 1), or None if units are incompatible or inputs invalid.
    """
    if required_qty is None or required_qty <= 0:
        return None
    if package_qty is None or package_qty <= 0:
        return None
    if not required_unit or not required_unit.strip():
        return None
    if not package_unit or not package_unit.strip():
        return None

    # Normalize both to base units using existing conversion system
    req_base_qty, req_base_unit = normalize_unit_and_quantity(required_qty, required_unit)
    pkg_base_qty, pkg_base_unit = normalize_unit_and_quantity(package_qty, package_unit)

    if req_base_qty is None or req_base_unit is None:
        return None
    if pkg_base_qty is None or pkg_base_unit is None:
        return None

    # Fast path: identical base unit dimension (e.g. g <-> kg, ml <-> L, piece <-> pieces)
    if req_base_unit == pkg_base_unit:
        packages = math.ceil(req_base_qty / pkg_base_qty)
        return max(1, packages)

    # Cross-dimension conversion using ingredient physical heuristics
    if ingredient_name:
        converted_req_qty = convert_cross_dimension_quantity(
            qty=req_base_qty,
            from_base_unit=req_base_unit,
            to_base_unit=pkg_base_unit,
            ingredient_name=ingredient_name,
            original_unit=required_unit,
        )
        if converted_req_qty is not None and converted_req_qty > 0:
            packages = math.ceil(converted_req_qty / pkg_base_qty)
            return max(1, packages)

    return None


def calculate_line_cost(
    packages_required: int,
    package_price: Optional[float],
) -> Optional[float]:
    """
    Calculate total line cost for a product selection.

    Returns:
        Line cost in INR, or None if price is invalid.
    """
    if packages_required < 1:
        return None
    if package_price is None:
        return None
    if package_price < 0:
        return None
    # Zero price is valid if data explicitly contains it
    return round(packages_required * package_price, 2)


def _get_delivery_fee_for_store(
    store_products: List[ProductMatchResult],
) -> float:
    """
    Determine delivery fee for a store based on product data.
    Uses existing stored delivery fees when available;
    falls back to CART_DEFAULT_DEMO_DELIVERY_FEE for demo data.
    """
    # In the current architecture, delivery_fee is on ProductPrice, not ProductMatchResult.
    # Demo stores use the configured default.
    return settings.CART_DEFAULT_DEMO_DELIVERY_FEE


def _select_best_product_for_ingredient(
    ingredient: CartIngredientRequest,
    candidates: List[ProductMatchResult],
) -> Optional[Tuple[ProductMatchResult, int, float]]:
    """
    Select the best valid product for an ingredient from a list of candidates.

    Selection priority:
      1. In-stock (price is not None and > 0 as proxy)
      2. Compatible units (packages_required is not None)
      3. Highest match score
      4. Lowest resulting line cost
      5. Deterministic product_id tie-breaker

    Returns:
        (product, packages_required, line_cost) or None if no valid candidate.
    """
    scored_candidates: List[Tuple[ProductMatchResult, int, float]] = []

    for product in candidates:
        # Never select products explicitly marked out of stock.
        if not product.availability:
            continue

        # Must have a valid price
        if product.price is None or product.price < 0:
            continue

        # Calculate packages
        packages = calculate_packages_required(
            required_qty=ingredient.required_quantity,
            required_unit=ingredient.required_unit,
            package_qty=product.package_quantity,
            package_unit=product.package_unit,
            ingredient_name=ingredient.ingredient_name,
        )
        if packages is None:
            continue

        line = calculate_line_cost(packages, product.price)
        if line is None:
            continue

        scored_candidates.append((product, packages, line))

    if not scored_candidates:
        return None

    # Sort by: highest match score DESC, lowest line cost ASC, product_id ASC (deterministic)
    scored_candidates.sort(
        key=lambda x: (-x[0].similarity_score, x[2], x[0].product_id)
    )

    return scored_candidates[0]


def build_store_baskets(
    ingredients: List[CartIngredientRequest],
    matched_products_by_ingredient: Dict[str, List[ProductMatchResult]],
) -> List[CartStoreBreakdown]:
    """
    Build per-store baskets from matched products.

    Groups products by store, selects the best product per ingredient per store,
    calculates package counts, line costs, delivery fees, and totals.
    """
    # Step 1: Collect all store IDs from matched products
    store_products: Dict[str, Dict[str, List[ProductMatchResult]]] = {}

    for ing in ingredients:
        matches = matched_products_by_ingredient.get(ing.ingredient_name, [])
        for product in matches:
            # Only consider matched products (passed threshold)
            if product.match_status != "matched":
                continue
            store_key = product.store_name or product.store_id or "Unknown Store"
            if store_key not in store_products:
                store_products[store_key] = {}
            if ing.ingredient_name not in store_products[store_key]:
                store_products[store_key][ing.ingredient_name] = []
            store_products[store_key][ing.ingredient_name].append(product)

    # Step 2: Build basket for each store
    baskets: List[CartStoreBreakdown] = []

    for store_name, ing_products in store_products.items():
        selected_products: List[CartProductSelection] = []
        missing: List[CartMissingIngredient] = []
        subtotal = 0.0

        # Extract store_id from any product in this store
        any_product = None
        for prod_list in ing_products.values():
            if prod_list:
                any_product = prod_list[0]
                break
        store_id = any_product.store_id if any_product else None

        for ing in ingredients:
            candidates = ing_products.get(ing.ingredient_name, [])
            if not candidates:
                missing.append(CartMissingIngredient(
                    ingredient_name=ing.ingredient_name,
                    reason="No compatible in-stock product found at this store"
                ))
                continue

            selection = _select_best_product_for_ingredient(ing, candidates)
            if selection is None:
                missing.append(CartMissingIngredient(
                    ingredient_name=ing.ingredient_name,
                    reason="No compatible package size or valid price available"
                ))
                continue

            product, packages, line_cost = selection
            subtotal += line_cost

            selected_products.append(CartProductSelection(
                ingredient_name=ing.ingredient_name,
                product_id=product.product_id,
                product_name=product.product_name,
                store_id=product.store_id,
                store_name=product.store_name,
                brand=product.brand,
                package_quantity=product.package_quantity,
                package_unit=product.package_unit,
                packages_required=packages,
                package_price=product.price,
                line_cost=line_cost,
                currency="INR",
                match_score=product.similarity_score,
                in_stock=True,
                data_source_type=product.data_source_type or "demo",
                price_freshness=product.price_freshness or "CACHED",
            ))

        delivery_fee = _get_delivery_fee_for_store([])
        total = round(subtotal + delivery_fee, 2)
        complete = len(missing) == 0 and len(selected_products) == len(ingredients)

        baskets.append(CartStoreBreakdown(
            store_id=store_id,
            store_name=store_name,
            selected_products=selected_products,
            missing_ingredients=missing,
            subtotal=round(subtotal, 2),
            delivery_fee=delivery_fee,
            total=total,
            complete=complete,
        ))

    # Step 3: Add baskets for stores that have zero products for any ingredient
    # (stores not represented in any match are simply absent — correct behavior)

    return baskets


# ---------------------------------------------------------------------------
# STRATEGY 1 — Cheapest Single Store
# ---------------------------------------------------------------------------

def strategy_cheapest_single_store(
    baskets: List[CartStoreBreakdown],
) -> Optional[CartStrategyResult]:
    """
    Find the cheapest complete basket from a single store.

    Only baskets with complete=True qualify.
    Sorted by total ascending with deterministic store_name tie-breaking.
    """
    complete_baskets = [b for b in baskets if b.complete]
    if not complete_baskets:
        return None

    complete_baskets.sort(key=lambda b: (b.total, b.store_name or ""))
    best = complete_baskets[0]

    return CartStrategyResult(
        strategy="cheapest_single_store",
        stores=[best],
        stores_used=1,
        total_cost=best.total,
        currency="INR",
        missing_ingredients=[],
        explanation=(
            f"Cheapest complete basket from a single store: {best.store_name}. "
            f"Subtotal ₹{best.subtotal:.2f} + delivery ₹{best.delivery_fee:.2f} = ₹{best.total:.2f}."
        ),
    )


# ---------------------------------------------------------------------------
# STRATEGY 2 — Cheapest Split Cart
# ---------------------------------------------------------------------------

def strategy_cheapest_split_cart(
    ingredients: List[CartIngredientRequest],
    matched_products_by_ingredient: Dict[str, List[ProductMatchResult]],
    max_stores: Optional[int] = None,
    min_split_saving: Optional[float] = None,
    single_store_total: Optional[float] = None,
) -> Optional[CartStrategyResult]:
    """
    Find the cheapest combination of products across multiple stores.

    Rules:
      - Pick cheapest valid product for each ingredient across all stores.
      - Add delivery fee for each distinct store used.
      - Respect max_stores limit.
      - Only recommend if saving >= min_split_saving vs single_store_total.
    """
    if max_stores is None:
        max_stores = settings.CART_MAX_STORES
    if min_split_saving is None:
        min_split_saving = settings.CART_MIN_SPLIT_SAVING

    # Step 1: Find cheapest valid product per ingredient
    cheapest_per_ingredient: Dict[str, Tuple[ProductMatchResult, int, float]] = {}
    missing: List[CartMissingIngredient] = []

    for ing in ingredients:
        matches = matched_products_by_ingredient.get(ing.ingredient_name, [])
        # Only matched products
        valid_matches = [m for m in matches if m.match_status == "matched"]

        best = _select_best_product_for_ingredient(ing, valid_matches)
        if best is None:
            missing.append(CartMissingIngredient(
                ingredient_name=ing.ingredient_name,
                reason="No compatible in-stock product found across any store"
            ))
            continue

        # Among all valid candidates, pick the one with lowest line cost
        # (overrides match-score priority for split cart cost optimization)
        all_scored: List[Tuple[ProductMatchResult, int, float]] = []
        for product in valid_matches:
            if not product.availability:
                continue
            if product.price is None or product.price < 0:
                continue
            packages = calculate_packages_required(
                ing.required_quantity, ing.required_unit,
                product.package_quantity, product.package_unit,
                ingredient_name=ing.ingredient_name,
            )
            if packages is None:
                continue
            line = calculate_line_cost(packages, product.price)
            if line is None:
                continue
            all_scored.append((product, packages, line))

        if not all_scored:
            missing.append(CartMissingIngredient(
                ingredient_name=ing.ingredient_name,
                reason="No compatible package size or valid price available"
            ))
            continue

        # Sort by: lowest line cost, then highest match score, then product_id
        all_scored.sort(key=lambda x: (x[2], -x[0].similarity_score, x[0].product_id))
        cheapest_per_ingredient[ing.ingredient_name] = all_scored[0]

    if not cheapest_per_ingredient:
        return None

    # Step 2: Determine stores used
    stores_used_set = set()
    for ing_name, (product, packages, line_cost) in cheapest_per_ingredient.items():
        store_key = product.store_name or product.store_id or "Unknown Store"
        stores_used_set.add(store_key)

    # Step 3: Check max_stores limit
    if len(stores_used_set) > max_stores:
        # Try to find a valid combination within the store limit
        result = _find_best_split_within_limit(
            ingredients, matched_products_by_ingredient,
            max_stores, missing
        )
        if result is None:
            return None
        cheapest_per_ingredient, stores_used_set, missing = result

    # Step 4: Build store breakdowns
    store_breakdowns: Dict[str, CartStoreBreakdown] = {}
    for ing_name, (product, packages, line_cost) in cheapest_per_ingredient.items():
        store_key = product.store_name or product.store_id or "Unknown Store"
        if store_key not in store_breakdowns:
            store_breakdowns[store_key] = CartStoreBreakdown(
                store_id=product.store_id,
                store_name=store_key,
                selected_products=[],
                missing_ingredients=[],
                subtotal=0.0,
                delivery_fee=_get_delivery_fee_for_store([]),
                total=0.0,
                complete=True,
            )

        bd = store_breakdowns[store_key]
        bd.selected_products.append(CartProductSelection(
            ingredient_name=ing_name,
            product_id=product.product_id,
            product_name=product.product_name,
            store_id=product.store_id,
            store_name=product.store_name,
            brand=product.brand,
            package_quantity=product.package_quantity,
            package_unit=product.package_unit,
            packages_required=packages,
            package_price=product.price,
            line_cost=line_cost,
            currency="INR",
            match_score=product.similarity_score,
            in_stock=True,
            data_source_type=product.data_source_type or "demo",
            price_freshness=product.price_freshness or "CACHED",
        ))
        bd.subtotal = round(bd.subtotal + line_cost, 2)

    # Update totals
    for bd in store_breakdowns.values():
        bd.total = round(bd.subtotal + bd.delivery_fee, 2)

    # Step 5: Calculate total
    split_total = round(sum(bd.total for bd in store_breakdowns.values()), 2)

    # Step 6: Check if savings are sufficient
    if single_store_total is not None:
        saving = round(single_store_total - split_total, 2)
        if saving < min_split_saving:
            return None
    else:
        saving = 0.0

    stores_list = sorted(store_breakdowns.values(), key=lambda b: b.store_name)
    store_names = [b.store_name for b in stores_list]

    return CartStrategyResult(
        strategy="cheapest_split_cart",
        stores=stores_list,
        stores_used=len(stores_list),
        total_cost=split_total,
        currency="INR",
        missing_ingredients=missing,
        explanation=(
            f"Split cart across {len(stores_list)} stores: {', '.join(store_names)}. "
            f"Total ₹{split_total:.2f}"
            + (f", saving ₹{saving:.2f} vs cheapest single store." if saving > 0 else ".")
        ),
    )


def _find_best_split_within_limit(
    ingredients: List[CartIngredientRequest],
    matched_products_by_ingredient: Dict[str, List[ProductMatchResult]],
    max_stores: int,
    existing_missing: List[CartMissingIngredient],
) -> Optional[Tuple[Dict, set, List[CartMissingIngredient]]]:
    """
    Find the cheapest valid split-cart combination using at most max_stores stores.
    """
    # Collect all candidate stores
    all_stores: set = set()
    for ing in ingredients:
        matches = matched_products_by_ingredient.get(ing.ingredient_name, [])
        for m in matches:
            if m.match_status == "matched":
                store_key = m.store_name or m.store_id or "Unknown Store"
                all_stores.add(store_key)

    if not all_stores:
        return None

    best_combo = None
    best_total = float("inf")

    # Try all store combinations up to max_stores
    for r in range(1, min(max_stores, len(all_stores)) + 1):
        for combo in combinations(sorted(all_stores), r):
            combo_set = set(combo)
            result = _evaluate_store_combo(ingredients, matched_products_by_ingredient, combo_set)
            if result is None:
                continue
            cheapest, total, combo_missing = result
            if total < best_total:
                best_total = total
                best_combo = (cheapest, combo_set, combo_missing)

    return best_combo


def _evaluate_store_combo(
    ingredients: List[CartIngredientRequest],
    matched_products_by_ingredient: Dict[str, List[ProductMatchResult]],
    allowed_stores: set,
) -> Optional[Tuple[Dict, float, List[CartMissingIngredient]]]:
    """Evaluate a specific combination of stores for a split cart."""
    cheapest: Dict[str, Tuple[ProductMatchResult, int, float]] = {}
    missing: List[CartMissingIngredient] = []

    for ing in ingredients:
        matches = matched_products_by_ingredient.get(ing.ingredient_name, [])
        valid = [
            m for m in matches
            if m.match_status == "matched"
            and (m.store_name or m.store_id or "Unknown Store") in allowed_stores
        ]

        all_scored: List[Tuple[ProductMatchResult, int, float]] = []
        for product in valid:
            if not product.availability:
                continue
            if product.price is None or product.price < 0:
                continue
            packages = calculate_packages_required(
                ing.required_quantity, ing.required_unit,
                product.package_quantity, product.package_unit,
                ingredient_name=ing.ingredient_name,
            )
            if packages is None:
                continue
            line = calculate_line_cost(packages, product.price)
            if line is None:
                continue
            all_scored.append((product, packages, line))

        if not all_scored:
            missing.append(CartMissingIngredient(
                ingredient_name=ing.ingredient_name,
                reason="No compatible product in selected stores"
            ))
            continue

        all_scored.sort(key=lambda x: (x[2], -x[0].similarity_score, x[0].product_id))
        cheapest[ing.ingredient_name] = all_scored[0]

    if not cheapest:
        return None

    # Calculate total with delivery fees per store
    stores_used = set()
    subtotal = 0.0
    for ing_name, (product, packages, line_cost) in cheapest.items():
        subtotal += line_cost
        stores_used.add(product.store_name or product.store_id or "Unknown Store")

    delivery_total = len(stores_used) * settings.CART_DEFAULT_DEMO_DELIVERY_FEE
    total = round(subtotal + delivery_total, 2)

    return cheapest, total, missing


# ---------------------------------------------------------------------------
# STRATEGY 3 — Fastest Available
# ---------------------------------------------------------------------------

def strategy_fastest_available(
    baskets: List[CartStoreBreakdown],
) -> Optional[CartStrategyResult]:
    """
    Availability-based ranking strategy.

    Does NOT fabricate delivery ETAs. Uses deterministic ranking:
      1. Complete baskets first
      2. Highest number of available products
      3. Fewest missing ingredients
      4. Lowest total cost (tie-breaker)
      5. Deterministic store name (tie-breaker)
    """
    if not baskets:
        return None

    ranked = sorted(
        baskets,
        key=lambda b: (
            not b.complete,                    # complete first
            -len(b.selected_products),         # most products available
            len(b.missing_ingredients),        # fewest missing
            b.total,                           # cheapest
            b.store_name or "",                # deterministic
        ),
    )

    best = ranked[0]

    return CartStrategyResult(
        strategy="fastest_available",
        stores=[best],
        stores_used=1,
        total_cost=best.total,
        currency="INR",
        missing_ingredients=best.missing_ingredients,
        explanation=(
            f"Availability-based recommendation: {best.store_name} "
            f"with {len(best.selected_products)} available products. "
            f"Total ₹{best.total:.2f}. "
            "Note: This is an availability-based ranking, not a real-time delivery estimate."
        ),
    )
