"""
DishIQ Phase 6.3 — Grocery Price Comparison Service
Ranks semantically matched products by price (package price or normalized unit price),
handles multi-store options, excludes invalid prices, and selects the best/cheapest option.
"""
from typing import List, Optional, Tuple, Dict, Any

from app.product_matching.schemas import ProductMatchResult, BestProductOption
from app.product_matching.unit_pricing import calculate_unit_price


class PriceComparisonService:
    """
    Service for comparing prices of semantically matched grocery products.
    """

    @staticmethod
    def compare_and_rank_prices(
        results: List[ProductMatchResult],
        sort_by_price: bool = False,
    ) -> Tuple[List[ProductMatchResult], Optional[BestProductOption], Optional[str]]:
        """
        Process a list of ProductMatchResult items:
          1. Calculate normalized unit prices (e.g. ₹/g, ₹/ml, ₹/piece).
          2. Rank products by price (preferring unit_price when available and compatible).
          3. Exclude products with missing/invalid price (<= 0) from price ranking.
          4. Select the single best/cheapest option.
          5. Optionally sort results by price rank.

        Returns:
            (processed_results, best_option, comparison_mode)
        """
        if not results:
            return [], None, None

        # 1. Enrich items with calculated unit prices and ensure INR currency
        valid_items: List[ProductMatchResult] = []
        base_units: set = set()

        for item in results:
            item.currency = "INR"
            if item.price is not None and item.price > 0:
                u_price, b_unit = calculate_unit_price(
                    price=item.price,
                    quantity=item.package_quantity,
                    unit_str=item.package_unit,
                )
                item.unit_price = u_price
                item.base_unit = b_unit

                if u_price is not None and b_unit is not None:
                    base_units.add(b_unit)

                valid_items.append(item)
            else:
                item.price_rank = None
                item.unit_price = None
                item.base_unit = None

        if not valid_items:
            return results, None, None

        # 2. Determine comparison mode:
        has_unit_prices = (
            len(base_units) == 1 and all(item.unit_price is not None for item in valid_items)
        )
        comparison_mode = "unit_price" if has_unit_prices else "package_price"

        # 3. Sort valid items ascending by package price (x.price), breaking ties with unit_price and similarity_score
        valid_items.sort(
            key=lambda x: (
                x.price,
                x.unit_price if x.unit_price is not None else x.price,
                -x.similarity_score,
            )
        )

        # 4. Assign 1-indexed price_rank
        for idx, item in enumerate(valid_items):
            item.price_rank = idx + 1

        # 5. Build BestProductOption from the top price-ranked item
        cheapest_item = valid_items[0]
        best_option = BestProductOption(
            product_id=cheapest_item.product_id,
            product_name=cheapest_item.product_name,
            store_id=cheapest_item.store_id,
            store_name=cheapest_item.store_name,
            brand=cheapest_item.brand,
            category=cheapest_item.category,
            price=cheapest_item.price,
            currency="INR",
            package_quantity=cheapest_item.package_quantity,
            package_unit=cheapest_item.package_unit,
            unit_price=cheapest_item.unit_price,
            base_unit=cheapest_item.base_unit,
            similarity_score=cheapest_item.similarity_score,
        )

        # 6. If sort_by_price requested, reorder results array by price rank
        if sort_by_price:
            invalid_items = [item for item in results if item.price is None or item.price <= 0]
            final_results = valid_items + invalid_items
        else:
            final_results = results

        return final_results, best_option, comparison_mode
