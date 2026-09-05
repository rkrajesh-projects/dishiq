"""
DishIQ Phase 7.1–7.3 — Cart Optimization Tests
Comprehensive tests for package calculation, store baskets, and shopping strategies.
"""
import pytest
from typing import List, Dict, Optional

from app.schemas.cart import (
    CartIngredientRequest,
    CartCompareRequest,
    CartProductSelection,
    CartStoreBreakdown,
    CartMissingIngredient,
    CartStrategyResult,
    CartOptimizeResponse,
)
from app.product_matching.schemas import ProductMatchResult
from app.services.cart_optimization_service import (
    calculate_packages_required,
    calculate_line_cost,
    build_store_baskets,
    strategy_cheapest_single_store,
    strategy_cheapest_split_cart,
    strategy_fastest_available,
)
from app.core.config import settings


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _make_product(
    product_id: str = "p1",
    product_name: str = "Test Product",
    store_id: str = "s1",
    store_name: str = "Store A",
    price: Optional[float] = 100.0,
    package_quantity: Optional[float] = 500.0,
    package_unit: Optional[str] = "g",
    similarity_score: float = 0.90,
    match_status: str = "matched",
    brand: str = "TestBrand",
) -> ProductMatchResult:
    return ProductMatchResult(
        product_id=product_id,
        product_name=product_name,
        brand=brand,
        category="TestCategory",
        store_id=store_id,
        store_name=store_name,
        price=price,
        currency="INR",
        package_quantity=package_quantity,
        package_unit=package_unit,
        unit_price=None,
        base_unit=None,
        similarity_score=similarity_score,
        matched_text=product_name.lower(),
        match_status=match_status,
        rank=1,
        price_rank=None,
    )


def _make_ingredient(
    name: str = "paneer",
    qty: float = 500.0,
    unit: str = "g",
) -> CartIngredientRequest:
    return CartIngredientRequest(
        ingredient_name=name,
        required_quantity=qty,
        required_unit=unit,
    )


# ===================================================================
# 1. PACKAGE CALCULATION TESTS
# ===================================================================

class TestPackageCalculation:

    def test_exact_package(self):
        """500g required, 500g package → 1 package."""
        assert calculate_packages_required(500, "g", 500, "g") == 1

    def test_partial_package(self):
        """500g required, 200g package → 3 packages (ceil(2.5))."""
        assert calculate_packages_required(500, "g", 200, "g") == 3

    def test_multiple_packages(self):
        """1000g required, 250g package → 4 packages."""
        assert calculate_packages_required(1000, "g", 250, "g") == 4

    def test_kg_to_g_conversion(self):
        """1kg required, 250g package → 4 packages."""
        assert calculate_packages_required(1, "kg", 250, "g") == 4

    def test_g_to_kg_conversion(self):
        """500g required, 1kg package → 1 package (500g < 1000g)."""
        assert calculate_packages_required(500, "g", 1, "kg") == 1

    def test_ml_to_litre_conversion(self):
        """500ml required, 1 litre package → 1 package."""
        assert calculate_packages_required(500, "ml", 1, "litre") == 1

    def test_litre_to_ml_conversion(self):
        """2 litres required, 500 ml package → 4 packages."""
        assert calculate_packages_required(2, "litre", 500, "ml") == 4

    def test_incompatible_units(self):
        """g required, ml package → None (incompatible)."""
        assert calculate_packages_required(500, "g", 500, "ml") is None

    def test_null_required_quantity(self):
        assert calculate_packages_required(None, "g", 500, "g") is None

    def test_zero_required_quantity(self):
        assert calculate_packages_required(0, "g", 500, "g") is None

    def test_negative_required_quantity(self):
        assert calculate_packages_required(-100, "g", 500, "g") is None

    def test_zero_package_quantity(self):
        assert calculate_packages_required(500, "g", 0, "g") is None

    def test_null_package_quantity(self):
        assert calculate_packages_required(500, "g", None, "g") is None

    def test_null_required_unit(self):
        assert calculate_packages_required(500, None, 500, "g") is None

    def test_null_package_unit(self):
        assert calculate_packages_required(500, "g", 500, None) is None

    def test_empty_unit_string(self):
        assert calculate_packages_required(500, "", 500, "g") is None

    def test_pieces_units(self):
        """3 pieces required, 1 piece package → 3 packages."""
        assert calculate_packages_required(3, "pieces", 1, "piece") == 3

    def test_small_decimal_quantity(self):
        """0.5 kg required, 200g package → ceil(500/200) = 3 packages."""
        assert calculate_packages_required(0.5, "kg", 200, "g") == 3


# ===================================================================
# 2. LINE COST TESTS
# ===================================================================

class TestLineCost:

    def test_normal_price(self):
        assert calculate_line_cost(3, 80.0) == 240.0

    def test_single_package(self):
        assert calculate_line_cost(1, 180.0) == 180.0

    def test_zero_price(self):
        """Zero price is valid if data explicitly contains it."""
        assert calculate_line_cost(2, 0.0) == 0.0

    def test_null_price(self):
        assert calculate_line_cost(2, None) is None

    def test_negative_price(self):
        assert calculate_line_cost(2, -50.0) is None

    def test_zero_packages(self):
        assert calculate_line_cost(0, 100.0) is None


# ===================================================================
# 3. STORE BASKET TESTS
# ===================================================================

class TestStoreBaskets:

    def test_one_complete_store(self):
        """Single store with all ingredients → complete basket."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [_make_product("p1", "Paneer 500g", "s1", "Store A", 180, 500, "g")]
        }
        baskets = build_store_baskets(ingredients, products)
        assert len(baskets) == 1
        assert baskets[0].complete is True
        assert baskets[0].subtotal == 180.0
        assert len(baskets[0].selected_products) == 1

    def test_multiple_stores(self):
        """Two stores with the same ingredient → two separate baskets."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [
                _make_product("p1", "Paneer 500g", "s1", "Store A", 180, 500, "g"),
                _make_product("p2", "Paneer 500g", "s2", "Store B", 160, 500, "g"),
            ]
        }
        baskets = build_store_baskets(ingredients, products)
        assert len(baskets) == 2

    def test_missing_ingredient(self):
        """Store has no paneer → missing ingredient, incomplete basket."""
        ingredients = [
            _make_ingredient("paneer", 500, "g"),
            _make_ingredient("tomato", 500, "g"),
        ]
        products = {
            "paneer": [_make_product("p1", "Paneer 500g", "s1", "Store A", 180, 500, "g")],
            "tomato": [],  # No tomato available
        }
        baskets = build_store_baskets(ingredients, products)
        store_a = [b for b in baskets if b.store_name == "Store A"][0]
        assert store_a.complete is False
        assert len(store_a.missing_ingredients) == 1
        assert store_a.missing_ingredients[0].ingredient_name == "tomato"

    def test_out_of_stock_product(self):
        """Product with null price is excluded as invalid."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [_make_product("p1", "Paneer 500g", "s1", "Store A", None, 500, "g")]
        }
        baskets = build_store_baskets(ingredients, products)
        if baskets:
            assert baskets[0].complete is False

    def test_delivery_fee_included(self):
        """Delivery fee is added to subtotal."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [_make_product("p1", "Paneer 500g", "s1", "Store A", 180, 500, "g")]
        }
        baskets = build_store_baskets(ingredients, products)
        assert baskets[0].delivery_fee == settings.CART_DEFAULT_DEMO_DELIVERY_FEE
        assert baskets[0].total == 180.0 + settings.CART_DEFAULT_DEMO_DELIVERY_FEE

    def test_irrelevant_low_score_product_excluded(self):
        """Low-confidence product should not appear in baskets."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [
                _make_product("p1", "Paneer Tikka Mix", "s1", "Store A", 60, 100, "g",
                              similarity_score=0.31, match_status="low_confidence"),
            ]
        }
        baskets = build_store_baskets(ingredients, products)
        # Low confidence products are filtered out
        assert len(baskets) == 0 or (baskets[0].complete is False)

    def test_product_selection_prefers_match_score(self):
        """Higher match score wins over lower price for same ingredient."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [
                _make_product("p1", "Fresh Paneer 500g", "s1", "Store A", 200, 500, "g",
                              similarity_score=0.95),
                _make_product("p2", "Paneer Tikka", "s1", "Store A", 60, 500, "g",
                              similarity_score=0.50),
            ]
        }
        baskets = build_store_baskets(ingredients, products)
        assert baskets[0].selected_products[0].product_id == "p1"

    def test_multiple_packages_cost(self):
        """500g required, 200g package → 3 packages × ₹80 = ₹240."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [_make_product("p1", "Paneer 200g", "s1", "Store A", 80, 200, "g")]
        }
        baskets = build_store_baskets(ingredients, products)
        sel = baskets[0].selected_products[0]
        assert sel.packages_required == 3
        assert sel.line_cost == 240.0


# ===================================================================
# 4. CHEAPEST SINGLE STORE STRATEGY TESTS
# ===================================================================

class TestCheapestSingleStore:

    def test_cheapest_complete_store(self):
        """Select cheapest among complete baskets."""
        baskets = [
            CartStoreBreakdown(
                store_id="s1", store_name="Store A",
                selected_products=[], missing_ingredients=[],
                subtotal=200, delivery_fee=30, total=230, complete=True,
            ),
            CartStoreBreakdown(
                store_id="s2", store_name="Store B",
                selected_products=[], missing_ingredients=[],
                subtotal=180, delivery_fee=30, total=210, complete=True,
            ),
        ]
        result = strategy_cheapest_single_store(baskets)
        assert result is not None
        assert result.strategy == "cheapest_single_store"
        assert result.total_cost == 210
        assert result.stores[0].store_name == "Store B"

    def test_incomplete_store_ignored(self):
        """Incomplete basket must not be selected."""
        baskets = [
            CartStoreBreakdown(
                store_id="s1", store_name="Store A",
                subtotal=100, delivery_fee=30, total=130, complete=False,
                missing_ingredients=[CartMissingIngredient(
                    ingredient_name="paneer", reason="Not found"
                )],
            ),
            CartStoreBreakdown(
                store_id="s2", store_name="Store B",
                subtotal=250, delivery_fee=30, total=280, complete=True,
            ),
        ]
        result = strategy_cheapest_single_store(baskets)
        assert result is not None
        assert result.stores[0].store_name == "Store B"

    def test_no_complete_store(self):
        """No complete basket → returns None."""
        baskets = [
            CartStoreBreakdown(
                store_id="s1", store_name="Store A",
                subtotal=100, delivery_fee=30, total=130, complete=False,
                missing_ingredients=[CartMissingIngredient(
                    ingredient_name="paneer", reason="Not found"
                )],
            ),
        ]
        result = strategy_cheapest_single_store(baskets)
        assert result is None

    def test_deterministic_tie_breaking(self):
        """Identical totals → deterministic by store name."""
        baskets = [
            CartStoreBreakdown(
                store_id="s2", store_name="Store B",
                subtotal=200, delivery_fee=30, total=230, complete=True,
            ),
            CartStoreBreakdown(
                store_id="s1", store_name="Store A",
                subtotal=200, delivery_fee=30, total=230, complete=True,
            ),
        ]
        result = strategy_cheapest_single_store(baskets)
        assert result is not None
        assert result.stores[0].store_name == "Store A"


# ===================================================================
# 5. CHEAPEST SPLIT CART STRATEGY TESTS
# ===================================================================

class TestCheapestSplitCart:

    def _setup_split_scenario(self):
        """Two ingredients, each cheaper at a different store."""
        ingredients = [
            _make_ingredient("paneer", 500, "g"),
            _make_ingredient("tomato", 500, "g"),
        ]
        products = {
            "paneer": [
                _make_product("p1", "Paneer 500g", "s1", "Store A", 200, 500, "g", 0.95),
                _make_product("p2", "Paneer 500g", "s2", "Store B", 150, 500, "g", 0.93),
            ],
            "tomato": [
                _make_product("p3", "Tomato 500g", "s1", "Store A", 40, 500, "g", 0.90),
                _make_product("p4", "Tomato 500g", "s2", "Store B", 80, 500, "g", 0.88),
            ],
        }
        return ingredients, products

    def test_split_cart_saves_enough(self):
        """Split cart recommended when saving >= MIN_SPLIT_SAVING."""
        ingredients, products = self._setup_split_scenario()
        # Single store: Store A = 200+40+30 = 270, Store B = 150+80+30 = 260
        # Split: Paneer from B (150) + Tomato from A (40) + delivery×2 (60) = 250
        # Saving = 260 - 250 = 10... that's less than default 50.
        # Let's use lower threshold:
        result = strategy_cheapest_split_cart(
            ingredients, products,
            max_stores=2, min_split_saving=5.0,
            single_store_total=260,
        )
        assert result is not None
        assert result.strategy == "cheapest_split_cart"
        assert result.stores_used <= 2

    def test_split_cart_saving_below_threshold(self):
        """Split cart NOT recommended when saving < MIN_SPLIT_SAVING."""
        ingredients, products = self._setup_split_scenario()
        result = strategy_cheapest_split_cart(
            ingredients, products,
            max_stores=2, min_split_saving=100.0,  # Very high threshold
            single_store_total=260,
        )
        assert result is None

    def test_split_cart_delivery_fees_for_both_stores(self):
        """Both store delivery fees included in split cart total."""
        ingredients = [
            _make_ingredient("paneer", 500, "g"),
            _make_ingredient("tomato", 500, "g"),
        ]
        products = {
            "paneer": [
                _make_product("p1", "Paneer 500g", "s1", "Store A", 100, 500, "g", 0.95),
            ],
            "tomato": [
                _make_product("p2", "Tomato 500g", "s2", "Store B", 50, 500, "g", 0.90),
            ],
        }
        result = strategy_cheapest_split_cart(
            ingredients, products,
            max_stores=2, min_split_saving=0.0,
            single_store_total=99999,  # Ensure split is always "worth it"
        )
        assert result is not None
        # Subtotal: 100 + 50 = 150. Delivery: 30×2 = 60. Total: 210
        delivery = settings.CART_DEFAULT_DEMO_DELIVERY_FEE
        expected_total = 100 + 50 + (delivery * 2)
        assert result.total_cost == expected_total

    def test_three_store_rejected_by_limit(self):
        """3 stores needed but max is 2 → find best within limit or None."""
        ingredients = [
            _make_ingredient("paneer", 500, "g"),
            _make_ingredient("tomato", 500, "g"),
            _make_ingredient("onion", 300, "g"),
        ]
        products = {
            "paneer": [
                _make_product("p1", "Paneer 500g", "s1", "Store A", 100, 500, "g", 0.95),
            ],
            "tomato": [
                _make_product("p2", "Tomato 500g", "s2", "Store B", 50, 500, "g", 0.90),
            ],
            "onion": [
                _make_product("p3", "Onion 500g", "s3", "Store C", 30, 500, "g", 0.88),
            ],
        }
        result = strategy_cheapest_split_cart(
            ingredients, products,
            max_stores=2, min_split_saving=0.0,
            single_store_total=99999,
        )
        # Each ingredient only at one unique store, so 2-store limit can't cover all 3
        assert result is None or result.stores_used <= 2

    def test_no_valid_split_cart(self):
        """No valid products → None."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {"paneer": []}
        result = strategy_cheapest_split_cart(
            ingredients, products,
            max_stores=2, min_split_saving=0.0,
            single_store_total=999,
        )
        assert result is None

    def test_split_cart_with_missing_ingredient(self):
        """Split cart with one ingredient missing reports it."""
        ingredients = [
            _make_ingredient("paneer", 500, "g"),
            _make_ingredient("saffron", 1, "g"),
        ]
        products = {
            "paneer": [
                _make_product("p1", "Paneer 500g", "s1", "Store A", 180, 500, "g", 0.95),
            ],
            "saffron": [],
        }
        result = strategy_cheapest_split_cart(
            ingredients, products,
            max_stores=2, min_split_saving=0.0,
            single_store_total=99999,
        )
        if result is not None:
            assert len(result.missing_ingredients) >= 1
            missing_names = [m.ingredient_name for m in result.missing_ingredients]
            assert "saffron" in missing_names


# ===================================================================
# 6. FASTEST AVAILABLE STRATEGY TESTS
# ===================================================================

class TestFastestAvailable:

    def test_complete_basket_preferred(self):
        """Complete basket ranks above incomplete."""
        baskets = [
            CartStoreBreakdown(
                store_id="s1", store_name="Store A",
                subtotal=300, delivery_fee=30, total=330, complete=False,
                missing_ingredients=[CartMissingIngredient(
                    ingredient_name="onion", reason="Not found"
                )],
                selected_products=[
                    CartProductSelection(
                        ingredient_name="paneer", product_id="p1", product_name="Paneer",
                        packages_required=1, line_cost=180, match_score=0.9,
                        data_source_type="demo", price_freshness="CACHED",
                    ),
                ],
            ),
            CartStoreBreakdown(
                store_id="s2", store_name="Store B",
                subtotal=350, delivery_fee=30, total=380, complete=True,
                selected_products=[
                    CartProductSelection(
                        ingredient_name="paneer", product_id="p2", product_name="Paneer",
                        packages_required=1, line_cost=200, match_score=0.9,
                        data_source_type="demo", price_freshness="CACHED",
                    ),
                    CartProductSelection(
                        ingredient_name="onion", product_id="p3", product_name="Onion",
                        packages_required=1, line_cost=50, match_score=0.85,
                        data_source_type="demo", price_freshness="CACHED",
                    ),
                ],
            ),
        ]
        result = strategy_fastest_available(baskets)
        assert result is not None
        assert result.strategy == "fastest_available"
        assert result.stores[0].store_name == "Store B"

    def test_no_fabricated_eta(self):
        """Explanation must NOT contain delivery time estimates."""
        baskets = [
            CartStoreBreakdown(
                store_id="s1", store_name="Store A",
                subtotal=200, delivery_fee=30, total=230, complete=True,
            ),
        ]
        result = strategy_fastest_available(baskets)
        assert result is not None
        assert "minutes" not in result.explanation.lower()
        assert "hours" not in result.explanation.lower()
        assert "arrives" not in result.explanation.lower()
        assert "availability" in result.explanation.lower()

    def test_deterministic_result(self):
        """Same input always produces same output."""
        baskets = [
            CartStoreBreakdown(
                store_id="s1", store_name="Store A",
                subtotal=200, delivery_fee=30, total=230, complete=True,
            ),
            CartStoreBreakdown(
                store_id="s2", store_name="Store B",
                subtotal=200, delivery_fee=30, total=230, complete=True,
            ),
        ]
        r1 = strategy_fastest_available(baskets)
        r2 = strategy_fastest_available(baskets)
        assert r1.stores[0].store_name == r2.stores[0].store_name

    def test_empty_baskets(self):
        assert strategy_fastest_available([]) is None


# ===================================================================
# 7. DATA SAFETY TESTS
# ===================================================================

class TestDataSafety:

    def test_demo_data_remains_cached(self):
        """Cart product selections from demo data must have CACHED freshness."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [_make_product("p1", "Paneer 500g", "s1", "Demo QuickMart", 180, 500, "g")]
        }
        baskets = build_store_baskets(ingredients, products)
        for basket in baskets:
            for sel in basket.selected_products:
                assert sel.price_freshness == "CACHED"
                assert sel.data_source_type == "demo"

    def test_demo_data_never_live(self):
        """No demo product should ever be marked LIVE."""
        ingredients = [_make_ingredient("paneer", 500, "g")]
        products = {
            "paneer": [_make_product("p1", "Paneer 500g", "s1", "Demo QuickMart", 180, 500, "g")]
        }
        baskets = build_store_baskets(ingredients, products)
        for basket in baskets:
            for sel in basket.selected_products:
                assert sel.price_freshness != "LIVE"


# ===================================================================
# 8. SCHEMA VALIDATION TESTS
# ===================================================================

class TestSchemaValidation:

    def test_cart_ingredient_request_valid(self):
        ing = CartIngredientRequest(
            ingredient_name="paneer", required_quantity=500, required_unit="g"
        )
        assert ing.ingredient_name == "paneer"

    def test_cart_ingredient_request_blank_name(self):
        with pytest.raises(Exception):
            CartIngredientRequest(
                ingredient_name="", required_quantity=500, required_unit="g"
            )

    def test_cart_ingredient_request_zero_quantity(self):
        with pytest.raises(Exception):
            CartIngredientRequest(
                ingredient_name="paneer", required_quantity=0, required_unit="g"
            )

    def test_cart_ingredient_request_negative_quantity(self):
        with pytest.raises(Exception):
            CartIngredientRequest(
                ingredient_name="paneer", required_quantity=-1, required_unit="g"
            )

    def test_cart_ingredient_request_blank_unit(self):
        with pytest.raises(Exception):
            CartIngredientRequest(
                ingredient_name="paneer", required_quantity=500, required_unit=""
            )

    def test_cart_compare_request_valid(self):
        req = CartCompareRequest(
            ingredients=[
                CartIngredientRequest(
                    ingredient_name="paneer", required_quantity=500, required_unit="g"
                ),
            ]
        )
        assert len(req.ingredients) == 1

    def test_cart_compare_request_empty(self):
        with pytest.raises(Exception):
            CartCompareRequest(ingredients=[])

    def test_cart_missing_ingredient_model(self):
        m = CartMissingIngredient(
            ingredient_name="saffron",
            reason="No compatible in-stock product found"
        )
        assert m.ingredient_name == "saffron"

    def test_cart_product_selection_model(self):
        sel = CartProductSelection(
            ingredient_name="paneer",
            product_id="p1",
            product_name="Paneer 500g",
            packages_required=1,
            line_cost=180.0,
            match_score=0.9,
            data_source_type="demo",
            price_freshness="CACHED",
        )
        assert sel.currency == "INR"
        assert sel.price_freshness == "CACHED"
