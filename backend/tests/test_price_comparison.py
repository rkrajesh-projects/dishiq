"""
DishIQ Phase 6.3 — Unit Tests for Price Comparison & Unit Pricing
Tests unit price calculations, price ranking, cheapest option selection, and store comparison.
"""
import pytest
from app.product_matching.unit_pricing import (
    normalize_unit_and_quantity,
    calculate_unit_price,
)
from app.product_matching.schemas import ProductMatchResult
from app.services.price_comparison_service import PriceComparisonService


class TestUnitPricing:
    """
    Unit tests for quantity normalization and unit price calculation math.
    """

    def test_grams_unit_pricing(self):
        # 200g @ ₹90.25 -> 0.4513 ₹/g
        u_price, base_unit = calculate_unit_price(90.25, 200.0, "grams")
        assert base_unit == "g"
        assert abs(u_price - 0.4513) < 1e-4

    def test_kg_unit_pricing(self):
        # 1kg (1000g) @ ₹40.0 -> 0.04 ₹/g
        u_price, base_unit = calculate_unit_price(40.0, 1.0, "kg")
        assert base_unit == "g"
        assert abs(u_price - 0.04) < 1e-4

    def test_ml_and_liter_unit_pricing(self):
        # 250ml @ ₹68 -> 0.272 ₹/ml
        u_ml, unit_ml = calculate_unit_price(68.0, 250.0, "ml")
        assert unit_ml == "ml"
        assert abs(u_ml - 0.272) < 1e-4

        # 1L (1000ml) @ ₹165 -> 0.165 ₹/ml
        u_l, unit_l = calculate_unit_price(165.0, 1.0, "liter")
        assert unit_l == "ml"
        assert abs(u_l - 0.165) < 1e-4

    def test_invalid_or_missing_quantity(self):
        u_price, b_unit = calculate_unit_price(100.0, None, "grams")
        assert u_price is None
        assert b_unit is None

        u_price_zero, _ = calculate_unit_price(100.0, 0.0, "grams")
        assert u_price_zero is None

        u_price_neg, _ = calculate_unit_price(-50.0, 200.0, "grams")
        assert u_price_neg is None


class TestPriceComparisonService:
    """
    Unit tests for PriceComparisonService price ranking and cheapest selection.
    """

    def test_price_sorting_and_cheapest_selection(self):
        items = [
            ProductMatchResult(
                product_id="p1",
                product_name="Mother Dairy Paneer 250g",
                store_name="Demo FreshBasket",
                price=115.0,
                package_quantity=250.0,
                package_unit="grams",
                similarity_score=0.88,
                matched_text="paneer",
                match_status="matched",
                rank=1,
            ),
            ProductMatchResult(
                product_id="p2",
                product_name="Amul Fresh Paneer 200g",
                store_name="Demo QuickMart",
                price=95.0,
                package_quantity=200.0,
                package_unit="grams",
                similarity_score=0.92,
                matched_text="paneer",
                match_status="matched",
                rank=2,
            ),
            ProductMatchResult(
                product_id="p3",
                product_name="Amul Fresh Paneer 200g",
                store_name="Demo LocalGrocer",
                price=90.25,
                package_quantity=200.0,
                package_unit="grams",
                similarity_score=0.92,
                matched_text="paneer",
                match_status="matched",
                rank=3,
            ),
        ]

        results, best_opt, mode = PriceComparisonService.compare_and_rank_prices(
            items, sort_by_price=True
        )

        assert mode == "unit_price"
        assert best_opt is not None
        # Cheapest unit price (90.25 / 200g = 0.4513 ₹/g) is p3 from Demo LocalGrocer
        assert best_opt.product_id == "p3"
        assert best_opt.store_name == "Demo LocalGrocer"
        assert best_opt.price == 90.25
        assert best_opt.currency == "INR"

        # Unit prices ascending: p3 (0.451) < p1 (0.460) < p2 (0.475)
        assert results[0].product_id == "p3"
        assert results[0].price_rank == 1
        assert results[1].product_id == "p1"
        assert results[1].price_rank == 2
        assert results[2].product_id == "p2"
        assert results[2].price_rank == 3

    def test_missing_or_zero_price_handled_safely(self):
        items = [
            ProductMatchResult(
                product_id="p1",
                product_name="Paneer No Price",
                price=None,
                similarity_score=0.95,
                matched_text="paneer",
                match_status="matched",
                rank=1,
            ),
            ProductMatchResult(
                product_id="p2",
                product_name="Paneer Zero Price",
                price=0.0,
                similarity_score=0.94,
                matched_text="paneer",
                match_status="matched",
                rank=2,
            ),
            ProductMatchResult(
                product_id="p3",
                product_name="Amul Paneer 200g",
                price=95.0,
                package_quantity=200.0,
                package_unit="grams",
                similarity_score=0.90,
                matched_text="paneer",
                match_status="matched",
                rank=3,
            ),
        ]

        results, best_opt, mode = PriceComparisonService.compare_and_rank_prices(
            items, sort_by_price=True
        )

        # Invalid prices (None and 0.0) must not become cheapest
        assert best_opt is not None
        assert best_opt.product_id == "p3"
        assert best_opt.price == 95.0

        # p1 and p2 must have price_rank = None
        p1_res = [r for r in results if r.product_id == "p1"][0]
        assert p1_res.price_rank is None

    def test_no_valid_prices_returns_no_best_option(self):
        items = [
            ProductMatchResult(
                product_id="p1",
                product_name="Paneer No Price",
                price=None,
                similarity_score=0.95,
                matched_text="paneer",
                match_status="matched",
                rank=1,
            )
        ]
        results, best_opt, mode = PriceComparisonService.compare_and_rank_prices(items)
        assert best_opt is None
