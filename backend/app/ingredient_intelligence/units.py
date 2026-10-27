"""
DishIQ Phase 5 — Ingredient Intelligence
Centralized Unit System & Conversion Module.

Provides deterministic unit normalization, dimensionality classification,
compatibility checks, and safe quantity conversion across compatible units.
Prevents dangerous incompatible conversions (e.g. mass to volume without density).
"""
from __future__ import annotations

import enum
from typing import Dict, Optional, Tuple, Set


class UnitDimension(str, enum.Enum):
    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"
    DESCRIPTIVE = "descriptive"


# ---------------------------------------------------------------------------
# Unit Aliases -> Canonical Unit Identifier
# ---------------------------------------------------------------------------
UNIT_ALIAS_MAP: Dict[str, str] = {
    # Mass
    "g": "g",
    "gram": "g",
    "grams": "g",
    "gm": "g",
    "gms": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",

    # Volume
    "ml": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "l": "l",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
    "tsp": "tsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "ts": "tsp",
    "tbsp": "tbsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "tbs": "tbsp",
    "tb": "tbsp",
    "cup": "cup",
    "cups": "cup",
    "fl oz": "fl oz",
    "fluid ounce": "fl oz",
    "fluid ounces": "fl oz",
    "pt": "pt",
    "pint": "pt",
    "pints": "pt",
    "qt": "qt",
    "quart": "qt",
    "quarts": "qt",

    # Count
    "piece": "piece",
    "pieces": "piece",
    "pc": "piece",
    "pcs": "piece",
    "clove": "clove",
    "cloves": "clove",
    "head": "head",
    "heads": "head",
    "slice": "slice",
    "slices": "slice",
    "item": "piece",
    "items": "piece",
    "count": "piece",
    "unit": "piece",

    # Descriptive measures
    "pinch": "pinch",
    "pinches": "pinch",
    "handful": "handful",
    "handfuls": "handful",
    "bunch": "bunch",
    "bunches": "bunch",
    "dash": "dash",
    "dashes": "dash",
    "sprig": "sprig",
    "sprigs": "sprig",
    "can": "can",
    "cans": "can",
    "packet": "packet",
    "packets": "packet",
    "pack": "packet",
    "packs": "packet",
    "pkt": "packet",
    "pkts": "packet",
    "to taste": "to taste",
}

# ---------------------------------------------------------------------------
# Dimension Assignment
# ---------------------------------------------------------------------------
UNIT_DIMENSIONS: Dict[str, UnitDimension] = {
    # Mass
    "g": UnitDimension.MASS,
    "kg": UnitDimension.MASS,
    "mg": UnitDimension.MASS,
    "oz": UnitDimension.MASS,
    "lb": UnitDimension.MASS,

    # Volume
    "ml": UnitDimension.VOLUME,
    "l": UnitDimension.VOLUME,
    "tsp": UnitDimension.VOLUME,
    "tbsp": UnitDimension.VOLUME,
    "cup": UnitDimension.VOLUME,
    "fl oz": UnitDimension.VOLUME,
    "pt": UnitDimension.VOLUME,
    "qt": UnitDimension.VOLUME,

    # Count
    "piece": UnitDimension.COUNT,
    "clove": UnitDimension.COUNT,
    "head": UnitDimension.COUNT,
    "slice": UnitDimension.COUNT,

    # Descriptive
    "pinch": UnitDimension.DESCRIPTIVE,
    "handful": UnitDimension.DESCRIPTIVE,
    "bunch": UnitDimension.DESCRIPTIVE,
    "dash": UnitDimension.DESCRIPTIVE,
    "sprig": UnitDimension.DESCRIPTIVE,
    "can": UnitDimension.DESCRIPTIVE,
    "packet": UnitDimension.DESCRIPTIVE,
    "to taste": UnitDimension.DESCRIPTIVE,
}

# ---------------------------------------------------------------------------
# Base Unit Conversion Multipliers
# Base units: "g" for MASS, "ml" for VOLUME, "piece" for COUNT
# ---------------------------------------------------------------------------
UNIT_CONVERSION_FACTORS: Dict[str, float] = {
    # Mass -> base: g
    "g": 1.0,
    "kg": 1000.0,
    "mg": 0.001,
    "oz": 28.349523125,
    "lb": 453.59237,

    # Volume -> base: ml
    "ml": 1.0,
    "l": 1000.0,
    "tsp": 4.92892159375,
    "tbsp": 14.78676478125,
    "cup": 236.5882365,
    "fl oz": 29.5735295625,
    "pt": 473.176473,
    "qt": 946.352946,

    # Count -> base: piece
    "piece": 1.0,
    "clove": 1.0,
    "head": 1.0,
    "slice": 1.0,
}


def normalize_unit(unit_str: Optional[str]) -> Optional[str]:
    """
    Normalize unit spelling, capitalization, and common abbreviations to canonical form.
    Returns canonical unit string (e.g. 'g', 'kg', 'tbsp', 'cup') or None if input is invalid/empty.
    """
    if not unit_str or not unit_str.strip():
        return None
    cleaned = unit_str.strip().lower().rstrip(".")
    return UNIT_ALIAS_MAP.get(cleaned, cleaned)


def get_unit_dimension(unit_str: Optional[str]) -> Optional[UnitDimension]:
    """
    Return the physical dimension of the unit (MASS, VOLUME, COUNT, DESCRIPTIVE)
    or None if unrecognized.
    """
    canonical = normalize_unit(unit_str)
    if not canonical:
        return None
    return UNIT_DIMENSIONS.get(canonical)


def are_units_compatible(
    from_unit: Optional[str],
    to_unit: Optional[str],
    ingredient_name: Optional[str] = None,
) -> bool:
    """
    Check if two units can be converted into each other without external density or count parameters.
    Compatible if both share the exact same physical dimension (MASS to MASS, VOLUME to VOLUME, COUNT to COUNT).
    If ingredient_name is provided, cross-dimensional conversion is checked using ingredient physical heuristics.
    Descriptive units are only compatible with themselves unless heuristics apply.
    """
    c_from = normalize_unit(from_unit)
    c_to = normalize_unit(to_unit)
    if not c_from or not c_to:
        return False
    if c_from == c_to:
        return True

    dim_from = UNIT_DIMENSIONS.get(c_from)
    dim_to = UNIT_DIMENSIONS.get(c_to)

    if dim_from is None or dim_to is None:
        return False

    if dim_from == dim_to and dim_from != UnitDimension.DESCRIPTIVE:
        return True

    if ingredient_name:
        from app.product_matching.unit_pricing import convert_cross_dimension_quantity
        base_from = "g" if dim_from == UnitDimension.MASS else ("ml" if dim_from == UnitDimension.VOLUME else "piece")
        base_to = "g" if dim_to == UnitDimension.MASS else ("ml" if dim_to == UnitDimension.VOLUME else "piece")
        return convert_cross_dimension_quantity(1.0, base_from, base_to, ingredient_name, c_from) is not None

    # Descriptive units cannot convert across different descriptive units
    if dim_from == UnitDimension.DESCRIPTIVE or dim_to == UnitDimension.DESCRIPTIVE:
        return c_from == c_to

    return dim_from == dim_to


def convert_quantity(
    quantity: float,
    from_unit: Optional[str],
    to_unit: Optional[str],
    ingredient_name: Optional[str] = None,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Safely convert quantity between compatible units.
    Optionally accepts ingredient_name to enable cross-dimensional conversion
    using physical density and piece-weight heuristics.

    Returns:
        (converted_quantity, normalized_to_unit) if conversion succeeded.
        (None, error_reason) if units are incompatible, unknown, or quantity is invalid.
    """
    if quantity is None:
        return None, "Quantity cannot be None"

    c_from = normalize_unit(from_unit)
    c_to = normalize_unit(to_unit)

    if not c_from:
        return None, f"Unknown source unit '{from_unit}'"
    if not c_to:
        return None, f"Unknown target unit '{to_unit}'"

    if c_from == c_to:
        return round(quantity, 4), c_to

    dim_from = UNIT_DIMENSIONS.get(c_from)
    dim_to = UNIT_DIMENSIONS.get(c_to)

    if not dim_from:
        return None, f"Source unit '{c_from}' has unknown dimensionality"
    if not dim_to:
        return None, f"Target unit '{c_to}' has unknown dimensionality"

    if dim_from != dim_to or dim_from == UnitDimension.DESCRIPTIVE or dim_to == UnitDimension.DESCRIPTIVE:
        if ingredient_name:
            from app.product_matching.unit_pricing import convert_cross_dimension_quantity
            factor_from = UNIT_CONVERSION_FACTORS.get(c_from, 1.0)
            base_from = "g" if dim_from == UnitDimension.MASS else ("ml" if dim_from == UnitDimension.VOLUME else "piece")
            base_to = "g" if dim_to == UnitDimension.MASS else ("ml" if dim_to == UnitDimension.VOLUME else "piece")
            base_from_qty = quantity * factor_from
            converted_base = convert_cross_dimension_quantity(base_from_qty, base_from, base_to, ingredient_name, c_from)
            if converted_base is not None:
                factor_to = UNIT_CONVERSION_FACTORS.get(c_to, 1.0)
                target_qty = converted_base / factor_to
                return round(target_qty, 4), c_to

        return None, f"Incompatible conversion: cannot convert {dim_from.value} ('{c_from}') to {dim_to.value} ('{c_to}') without density"

    factor_from = UNIT_CONVERSION_FACTORS.get(c_from)
    factor_to = UNIT_CONVERSION_FACTORS.get(c_to)

    if factor_from is None or factor_to is None or factor_to == 0.0:
        return None, f"Conversion factors unavailable between '{c_from}' and '{c_to}'"

    # Convert to base unit, then to target unit
    base_qty = quantity * factor_from
    target_qty = base_qty / factor_to
    return round(target_qty, 4), c_to


def format_quantity_and_unit(quantity: Optional[float], unit: Optional[str]) -> str:
    """
    Format parsed quantity and unit for human display without rounding noise.
    e.g. (1.5, 'kg') -> '1.5 kg', (2.0, 'cup') -> '2 cups', (None, 'pinch') -> 'pinch'
    """
    c_unit = normalize_unit(unit) or (unit.strip() if unit else "")
    if quantity is None:
        return c_unit or ""

    # Integer display if whole number
    qty_str = str(int(quantity)) if quantity.is_integer() else f"{quantity:.2f}".rstrip("0").rstrip(".")

    if not c_unit:
        return qty_str

    # Simple pluralization for display
    if quantity > 1.0 and c_unit in {"cup", "piece", "clove", "slice", "pinch", "bunch", "packet", "can"}:
        disp_unit = f"{c_unit}s"
    else:
        disp_unit = c_unit

    return f"{qty_str} {disp_unit}"
