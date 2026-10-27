import re
from typing import List, Optional, Tuple, Dict, Any, Set

from app.product_matching.schemas import ProductMatchResult, BestProductOption
from app.product_matching.unit_pricing import (
    calculate_unit_price,
    calculate_standardized_unit_price,
    calculate_savings,
    normalize_unit_and_quantity,
)

CRITICAL_DESCRIPTORS = {
    'brown', 'basmati', 'white', 'red', 'green', 'black',
    'sharbati', 'organic', 'diet', 'sugar-free', 'vegan', 'gluten-free'
}

FORM_DESCRIPTORS = {
    'whole': {'whole', 'seeds', 'seed', 'stick', 'sticks', 'raw'},
    'ground': {'ground', 'powder', 'powdered', 'crushed', 'masala'},
    'paste': {'paste', 'puree'},
    'milk': {'milk'},
    'oil': {'oil'},
    'flour': {'flour', 'atta', 'maida', 'besan'},
    'flakes': {'flakes'},
    'butter': {'butter', 'ghee'},
    'extract': {'extract', 'essence'},
}


def _extract_core_words(name: str) -> Set[str]:
    if not name:
        return set()
    n = name.lower()
    # Remove pack size patterns
    n = re.sub(r'\b\d+(\.\d+)?\s*(kg|g|gm|ml|l|litre|liter|piece|pc|pcs)\b', '', n)
    return set(re.findall(r'\b[a-z]{3,}\b', n))


def _detect_form(words: Set[str]) -> Optional[str]:
    for form_category, form_words in FORM_DESCRIPTORS.items():
        if words.intersection(form_words):
            return form_category
    return None


def _check_comparability(anchor_name: str, candidate_name: str) -> Tuple[bool, Optional[str]]:
    w1 = _extract_core_words(anchor_name)
    w2 = _extract_core_words(candidate_name)

    # 1. Form check (e.g. coconut vs coconut milk, ground vs whole)
    form1 = _detect_form(w1)
    form2 = _detect_form(w2)
    if form1 and form2 and form1 != form2:
        return False, f"Different product form ({form1} vs {form2})"
    if (form1 == "milk" and "milk" not in w2) or (form2 == "milk" and "milk" not in w1):
        return False, "Different product form (milk vs raw)"
    if (form1 == "oil" and "oil" not in w2) or (form2 == "oil" and "oil" not in w1):
        return False, "Different product form (oil vs raw)"
    if (form1 in ["ground", "whole"] and not form2) or (form2 in ["ground", "whole"] and not form1):
        return False, f"Different product form ({form1 or form2} vs standard)"

    # 2. Critical descriptor check (organic, brown vs white, etc.)
    crit1 = w1.intersection(CRITICAL_DESCRIPTORS)
    crit2 = w2.intersection(CRITICAL_DESCRIPTORS)
    if crit1 != crit2:
        return False, f"Incompatible variant ({', '.join(crit1 or ['standard'])} vs {', '.join(crit2 or ['standard'])})"

    return True, None


class PriceComparisonService:
    @staticmethod
    def compare_and_rank_prices(
        results: List[ProductMatchResult],
        sort_by_price: bool = False,
        sort_by: str = "default",
    ) -> Tuple[List[ProductMatchResult], Optional[BestProductOption], Optional[str]]:
        """
        Compare products, validate eligibility, compute standardized unit prices,
        determine transparent ranking, and calculate honest savings against a baseline.
        
        Args:
            results: List of ProductMatchResult from semantic product matcher.
            sort_by_price: Legacy boolean flag (True -> rank by price).
            sort_by: Explicit sort criterion ('default', 'price_asc', 'unit_price_asc', 'best_value').
            
        Returns:
            (ranked_results, best_option, comparison_mode)
        """
        if not results:
            return [], None, None

        anchor_name = results[0].product_name
        base_units: Set[str] = set()
        seen = set()

        processed_items: List[ProductMatchResult] = []
        comparable_items: List[ProductMatchResult] = []
        incomparable_items: List[ProductMatchResult] = []

        # 1. Evaluate comparability, calculate unit prices, standardize displays
        for item in results:
            store = item.store_id or item.store_name or "unknown"
            dup_key = (store, item.product_name.lower(), item.package_quantity)
            if dup_key in seen:
                continue
            seen.add(dup_key)

            item.currency = "INR"

            # Check form & descriptor compatibility
            is_comp, comp_reason = _check_comparability(anchor_name, item.product_name)
            item.is_comparable = is_comp
            if not is_comp:
                item.comparison_notes = comp_reason

            # Validate price and quantity
            if item.price is not None and item.price > 0:
                base_p, base_u, std_p, std_u = calculate_standardized_unit_price(
                    price=item.price,
                    quantity=item.package_quantity,
                    unit_str=item.package_unit,
                )
                item.unit_price = base_p
                item.base_unit = base_u
                item.standardized_unit_price = std_p
                item.standardized_unit = std_u

                if base_u:
                    base_units.add(base_u)

                if is_comp and base_p is not None:
                    comparable_items.append(item)
                else:
                    if is_comp and base_p is None:
                        item.is_comparable = False
                        item.comparison_notes = "Package quantity unavailable for unit pricing"
                    incomparable_items.append(item)
            else:
                item.price_rank = None
                item.unit_price = None
                item.base_unit = None
                item.standardized_unit_price = None
                item.standardized_unit = None
                item.is_comparable = False
                item.comparison_notes = "Price unavailable or invalid"
                incomparable_items.append(item)

            processed_items.append(item)

        # 2. Determine comparison mode
        has_common_base_unit = len(base_units) == 1 and len(comparable_items) > 0
        if has_common_base_unit:
            comparison_mode = "unit_price"
        elif any(item.price is not None and item.price > 0 for item in processed_items):
            comparison_mode = "package_price"
        else:
            comparison_mode = None

        # 3. Transparent Ranking
        # Determine active sort mode
        effective_sort = sort_by
        if sort_by_price and effective_sort == "default":
            effective_sort = "best_value"

        def sort_key_unit_price(x: ProductMatchResult):
            # Sort by unit_price ascending, with high similarity tie-break, then deterministic tie-breaker
            primary = x.unit_price if (x.unit_price is not None and x.is_comparable) else float("inf")
            return (
                0 if getattr(x, "availability", True) else 1,
                primary,
                -x.similarity_score,
                x.product_name,
                x.product_id,
            )

        def sort_key_package_price(x: ProductMatchResult):
            # Sort by package price ascending
            primary = x.price if (x.price is not None and x.price > 0) else float("inf")
            return (
                0 if getattr(x, "availability", True) else 1,
                primary,
                -x.similarity_score,
                x.product_name,
                x.product_id,
            )

        def sort_key_best_value(x: ProductMatchResult):
            # Primary: unit price if available across group, else package price
            if has_common_base_unit:
                return sort_key_unit_price(x)
            return sort_key_package_price(x)

        # Partition available vs unavailable
        available_comp = [i for i in comparable_items if getattr(i, "availability", True)]
        unavailable_comp = [i for i in comparable_items if not getattr(i, "availability", True)]

        available_incomp = [i for i in incomparable_items if getattr(i, "availability", True)]
        unavailable_incomp = [i for i in incomparable_items if not getattr(i, "availability", True)]

        if effective_sort in ["unit_price", "unit_price_asc"]:
            available_comp.sort(key=sort_key_unit_price)
            unavailable_comp.sort(key=sort_key_unit_price)
            available_incomp.sort(key=sort_key_package_price)
            unavailable_incomp.sort(key=sort_key_package_price)
            ranked_comparable = available_comp + unavailable_comp
            final_incomparable = available_incomp + unavailable_incomp
        elif effective_sort in ["price_asc", "total_price"]:
            all_available = available_comp + available_incomp
            all_unavailable = unavailable_comp + unavailable_incomp
            all_available.sort(key=sort_key_package_price)
            all_unavailable.sort(key=sort_key_package_price)
            ranked_comparable = all_available + all_unavailable
            final_incomparable = []
        elif effective_sort == "best_value":
            available_comp.sort(key=sort_key_best_value)
            unavailable_comp.sort(key=sort_key_best_value)
            available_incomp.sort(key=sort_key_package_price)
            unavailable_incomp.sort(key=sort_key_package_price)
            ranked_comparable = available_comp + unavailable_comp
            final_incomparable = available_incomp + unavailable_incomp
        else:
            # Default order (similarity score preserved)
            ranked_comparable = processed_items
            final_incomparable = []

        # Assign 1-indexed price ranks to items with valid prices
        rank_counter = 1
        for item in ranked_comparable:
            if item.price is not None and item.price > 0:
                item.price_rank = rank_counter
                rank_counter += 1
            else:
                item.price_rank = None

        # 4. Calculate Transparent Savings against explicit baseline
        # Baseline is the highest-priced comparable option in the same data source group
        eligible_for_savings = [
            i for i in ranked_comparable
            if i.is_comparable and i.price is not None and i.price > 0
        ]

        # Group by data_source_type to avoid mixing live and demo prices
        source_groups: Dict[str, List[ProductMatchResult]] = {}
        for item in eligible_for_savings:
            src = item.data_source_type or "demo"
            source_groups.setdefault(src, []).append(item)

        for src, group in source_groups.items():
            if len(group) >= 2:
                # Reference product is highest priced in comparable group
                if has_common_base_unit:
                    ref_prod = max(group, key=lambda p: p.unit_price or 0.0)
                else:
                    ref_prod = max(group, key=lambda p: p.price or 0.0)

                for item in group:
                    if item.product_id != ref_prod.product_id:
                        s_amount, s_pct, s_warn = calculate_savings(
                            alternative_price=item.price,
                            reference_price=ref_prod.price,
                            alt_unit_price=item.unit_price,
                            ref_unit_price=ref_prod.unit_price,
                            alt_quantity=item.package_quantity,
                            ref_quantity=ref_prod.package_quantity,
                            alt_unit=item.package_unit,
                            ref_unit=ref_prod.package_unit,
                            alt_data_source=item.data_source_type,
                            ref_data_source=ref_prod.data_source_type,
                            alt_freshness=item.price_freshness,
                            ref_freshness=ref_prod.price_freshness,
                        )
                        if s_amount is not None and s_amount > 0:
                            item.savings_amount = s_amount
                            item.savings_percent = s_pct
                            item.reference_product_name = ref_prod.product_name

        # 5. Identify BestProductOption
        best_option = None
        available_cheapest = [
            i for i in ranked_comparable
            if getattr(i, "availability", True) and i.price is not None and i.price > 0
        ]
        if available_cheapest:
            top_item = available_cheapest[0]
            best_option = BestProductOption(
                product_id=top_item.product_id,
                product_name=top_item.product_name,
                store_id=top_item.store_id,
                store_name=top_item.store_name,
                brand=top_item.brand,
                category=top_item.category,
                price=top_item.price,
                currency="INR",
                package_quantity=top_item.package_quantity,
                package_unit=top_item.package_unit,
                unit_price=top_item.unit_price,
                base_unit=top_item.base_unit,
                standardized_unit_price=top_item.standardized_unit_price,
                standardized_unit=top_item.standardized_unit,
                savings_amount=top_item.savings_amount,
                savings_percent=top_item.savings_percent,
                reference_product_name=top_item.reference_product_name,
                comparison_notes=top_item.comparison_notes,
                availability=getattr(top_item, "availability", True),
                similarity_score=top_item.similarity_score,
                data_source_type=top_item.data_source_type,
                price_freshness=top_item.price_freshness,
            )

        final_results = ranked_comparable + final_incomparable
        return final_results, best_option, comparison_mode
