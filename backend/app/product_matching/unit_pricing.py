"""
DishIQ Phase 6.3 — Grocery Price Comparison
Unit Price Normalization & Calculation Module.

Provides deterministic conversion routines for mass (g/kg), volume (ml/l), and count (pieces/pack),
calculating normalized unit prices in INR (₹) per base unit.
"""
from typing import Optional, Tuple


# Unit categories and conversion factors to base units:
# Base units: "g" for mass, "ml" for volume, "piece" for count.
UNIT_CONVERSIONS = {
    # Mass (base unit: "g")
    "g": ("g", 1.0),
    "gram": ("g", 1.0),
    "grams": ("g", 1.0),
    "kg": ("g", 1000.0),
    "kilogram": ("g", 1000.0),
    "kilograms": ("g", 1000.0),
    
    # Volume (base unit: "ml")
    "ml": ("ml", 1.0),
    "milliliter": ("ml", 1.0),
    "milliliters": ("ml", 1.0),
    "l": ("ml", 1000.0),
    "liter": ("ml", 1000.0),
    "liters": ("ml", 1000.0),
    "litre": ("ml", 1000.0),
    "litres": ("ml", 1000.0),
    
    # Count / Items (base unit: "piece")
    "piece": ("piece", 1.0),
    "pieces": ("piece", 1.0),
    "cloves": ("piece", 1.0),
    "head": ("piece", 1.0),
    "bunch": ("piece", 1.0),
    "pack": ("piece", 1.0),
    "unit": ("piece", 1.0),
    "items": ("piece", 1.0),
    "count": ("piece", 1.0),
}


def normalize_unit_and_quantity(
    quantity: Optional[float],
    unit_str: Optional[str],
) -> Tuple[Optional[float], Optional[str]]:
    """
    Convert a package quantity and unit string into normalized base quantity and base unit.
    
    Returns:
        (base_quantity, base_unit) or (None, None) if unit is unmapped or quantity invalid.
    """
    if quantity is None or quantity <= 0 or not unit_str or not unit_str.strip():
        return None, None

    clean_unit = unit_str.strip().lower()
    conversion = UNIT_CONVERSIONS.get(clean_unit)

    if not conversion:
        return None, None

    base_unit, multiplier = conversion
    base_quantity = quantity * multiplier
    return base_quantity, base_unit


def calculate_unit_price(
    price: Optional[float],
    quantity: Optional[float],
    unit_str: Optional[str],
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate normalized unit price in INR per base unit (e.g. ₹/g, ₹/ml, ₹/piece).
    
    Returns:
        (unit_price, base_unit) or (None, None) if calculation is not possible.
    """
    if price is None or price <= 0:
        return None, None

    base_qty, base_unit = normalize_unit_and_quantity(quantity, unit_str)
    if base_qty is None or base_qty <= 0 or base_unit is None:
        return None, None

    unit_price = round(price / base_qty, 4)
    return unit_price, base_unit
