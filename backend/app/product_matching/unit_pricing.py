"""
DishIQ Phase 6.3 & Phase 8 — Grocery Price Comparison & Unit Pricing
Unit Price Normalization, Standardization & Savings Module.

Provides deterministic conversion routines for mass (g/kg), volume (ml/l), and count (pieces/pack),
calculating normalized unit prices in INR (₹) per base unit and consumer display unit (₹/kg, ₹/L, ₹/piece).
Includes rigorous, honest savings calculation rules.
"""
from typing import Dict, Optional, Tuple

try:
    from app.ingredient_intelligence.normalization import INGREDIENT_NORMALIZATION
except ImportError:
    INGREDIENT_NORMALIZATION = {}


# Unit categories and conversion factors to base units:
# Base units: "g" for mass, "ml" for volume, "piece" for count.
UNIT_CONVERSIONS = {
    # Mass (base unit: "g")
    "g": ("g", 1.0),
    "gram": ("g", 1.0),
    "grams": ("g", 1.0),
    "gm": ("g", 1.0),
    "kg": ("g", 1000.0),
    "kilogram": ("g", 1000.0),
    "kilograms": ("g", 1000.0),
    "mg": ("g", 0.001),
    "milligram": ("g", 0.001),
    "milligrams": ("g", 0.001),
    "oz": ("g", 28.3495),
    "ounce": ("g", 28.3495),
    "ounces": ("g", 28.3495),
    "lb": ("g", 453.5924),
    "lbs": ("g", 453.5924),
    "pound": ("g", 453.5924),
    "pounds": ("g", 453.5924),
    
    # Volume (base unit: "ml")
    "ml": ("ml", 1.0),
    "milliliter": ("ml", 1.0),
    "milliliters": ("ml", 1.0),
    "l": ("ml", 1000.0),
    "liter": ("ml", 1000.0),
    "liters": ("ml", 1000.0),
    "litre": ("ml", 1000.0),
    "litres": ("ml", 1000.0),
    "cup": ("ml", 236.588),
    "cups": ("ml", 236.588),
    "tbsp": ("ml", 14.7868),
    "tablespoon": ("ml", 14.7868),
    "tablespoons": ("ml", 14.7868),
    "tsp": ("ml", 4.9289),
    "teaspoon": ("ml", 4.9289),
    "teaspoons": ("ml", 4.9289),
    "fl oz": ("ml", 29.5735),
    "fluid ounce": ("ml", 29.5735),
    "pt": ("ml", 473.176),
    "pint": ("ml", 473.176),
    "qt": ("ml", 946.353),
    "quart": ("ml", 946.353),
    
    # Count / Items (base unit: "piece")
    "piece": ("piece", 1.0),
    "pieces": ("piece", 1.0),
    "clove": ("piece", 1.0),
    "cloves": ("piece", 1.0),
    "head": ("piece", 1.0),
    "heads": ("piece", 1.0),
    "slice": ("piece", 1.0),
    "slices": ("piece", 1.0),
    "bunch": ("piece", 1.0),
    "bunches": ("piece", 1.0),
    "pack": ("piece", 1.0),
    "packs": ("piece", 1.0),
    "packet": ("piece", 1.0),
    "packets": ("piece", 1.0),
    "pkt": ("piece", 1.0),
    "pkts": ("piece", 1.0),
    "unit": ("piece", 1.0),
    "units": ("piece", 1.0),
    "item": ("piece", 1.0),
    "items": ("piece", 1.0),
    "count": ("piece", 1.0),
    "sprig": ("piece", 1.0),
    "sprigs": ("piece", 1.0),
    "can": ("piece", 1.0),
    "cans": ("piece", 1.0),
    "bottle": ("piece", 1.0),
    "bottles": ("piece", 1.0),
}

# Standard consumer display units and multiplier from base unit:
STANDARDIZED_DISPLAY_UNITS = {
    "g": ("kg", 1000.0),      # ₹/g * 1000 = ₹/kg
    "ml": ("L", 1000.0),      # ₹/ml * 1000 = ₹/L
    "piece": ("piece", 1.0),  # ₹/piece
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


# ---------------------------------------------------------------------------
# Physical Culinary Heuristics (Piece Weight & Bulk Density)
# Used to bridge recipe dimension units (pieces, bunches, spoons)
# and grocery catalog units (grams, kilograms, millilitres, litres).
# ---------------------------------------------------------------------------

INGREDIENT_PIECE_WEIGHTS_GRAMS: Dict[str, float] = {
    # Vegetables & Produce
    "tomato": 100.0,
    "onion": 100.0,
    "potato": 150.0,
    "green chili": 5.0,
    "chili": 5.0,
    "chilli": 5.0,
    "coriander": 100.0,     # 1 standard retail bunch
    "mint": 50.0,          # 1 retail bunch
    "curry leaves": 10.0,  # 1 bunch / sprigs
    "lemon": 50.0,
    "lime": 40.0,
    "garlic": 4.0,         # 1 clove default
    "ginger": 15.0,        # 1 piece or ~1 inch
    "carrot": 100.0,
    "capsicum": 150.0,
    "bell pepper": 150.0,
    "cucumber": 200.0,
    "eggplant": 200.0,
    "brinjal": 200.0,
    "cauliflower": 500.0,  # 1 head
    "cabbage": 600.0,      # 1 head
    "beetroot": 120.0,
    "spinach": 200.0,      # 1 bunch
    "banana": 120.0,
    "apple": 150.0,

    # Dairy, Proteins & Staples
    "egg": 50.0,
    "paneer": 25.0,        # 1 cube / piece
    "bread": 30.0,        # 1 slice
    "tortilla": 40.0,
    "roti": 35.0,
    "chapati": 35.0,
}

INGREDIENT_DENSITIES_G_PER_ML: Dict[str, float] = {
    # Spices & Seeds (whole & ground)
    "cumin seeds": 0.65,
    "cumin": 0.65,
    "jeera": 0.65,
    "mustard seeds": 0.75,
    "mustard": 0.75,
    "rai": 0.75,
    "turmeric powder": 0.60,
    "turmeric": 0.60,
    "haldi": 0.60,
    "red chili powder": 0.60,
    "chili powder": 0.60,
    "coriander powder": 0.50,
    "coriander seeds": 0.40,
    "garam masala": 0.60,
    "black pepper": 0.70,
    "pepper": 0.70,
    "fenugreek": 0.70,
    "methi seeds": 0.70,
    "kasuri methi": 0.25,
    "cardamom": 0.60,
    "cinnamon": 0.55,
    "clove": 0.60,
    "ground clove": 0.60,
    "salt": 1.20,
    "table salt": 1.20,
    "sugar": 0.85,

    # Oils & Fats
    "oil": 0.92,
    "cooking oil": 0.92,
    "vegetable oil": 0.92,
    "olive oil": 0.92,
    "mustard oil": 0.92,
    "sunflower oil": 0.92,
    "sesame oil": 0.92,
    "coconut oil": 0.92,
    "ghee": 0.90,
    "butter": 0.95,

    # Liquids & Dairy
    "milk": 1.03,
    "water": 1.00,
    "curd": 1.00,
    "yogurt": 1.00,
    "dahi": 1.00,
    "buttermilk": 1.02,
    "heavy cream": 1.00,
    "cream": 1.00,
    "soy sauce": 1.15,
    "vinegar": 1.01,
    "lemon juice": 1.03,
    "honey": 1.42,

    # Flours & Grains
    "flour": 0.55,
    "wheat flour": 0.55,
    "all-purpose flour": 0.55,
    "maida": 0.55,
    "atta": 0.55,
    "besan": 0.55,
    "rice flour": 0.60,
    "cornstarch": 0.60,
    "rice": 0.85,
    "basmati rice": 0.85,
    "toor dal": 0.85,
    "chana": 0.80,
    "dal": 0.85,
}


def resolve_ingredient_piece_weight(
    ingredient_name: Optional[str],
    unit_str: Optional[str] = None,
) -> Optional[float]:
    """
    Resolve estimated weight in grams for 1 piece/unit of an ingredient.
    Considers specific units like 'clove', 'head', 'bunch', 'slice'.
    """
    if not ingredient_name or not ingredient_name.strip():
        return None

    clean_name = ingredient_name.strip().lower()
    clean_unit = unit_str.strip().lower() if unit_str else None

    # Unit-specific physical overrides
    if clean_unit in {"clove", "cloves"}:
        return 4.0
    if clean_unit in {"head", "heads", "bulb", "bulbs"}:
        if "garlic" in clean_name:
            return 35.0
        if "cabbage" in clean_name:
            return 600.0
        if "cauliflower" in clean_name:
            return 500.0
        return 300.0
    if clean_unit in {"slice", "slices"}:
        if "bread" in clean_name:
            return 30.0
        if "cheese" in clean_name:
            return 20.0
        return 25.0
    if clean_unit in {"bunch", "bunches"}:
        if "spinach" in clean_name or "palak" in clean_name:
            return 200.0
        if "mint" in clean_name or "pudina" in clean_name:
            return 50.0
        if "curry" in clean_name:
            return 10.0
        return 100.0  # default bunch weight (coriander, spring onion, etc.)

    # Check canonical dictionary lookup first
    canon = INGREDIENT_NORMALIZATION.get(clean_name, clean_name)
    if canon in INGREDIENT_PIECE_WEIGHTS_GRAMS:
        return INGREDIENT_PIECE_WEIGHTS_GRAMS[canon]

    # Substring matching (longer keys checked first)
    for key in sorted(INGREDIENT_PIECE_WEIGHTS_GRAMS.keys(), key=len, reverse=True):
        if key in clean_name:
            return INGREDIENT_PIECE_WEIGHTS_GRAMS[key]

    return None


def resolve_ingredient_density(ingredient_name: Optional[str]) -> Optional[float]:
    """
    Resolve estimated density in g/ml for an ingredient.
    """
    if not ingredient_name or not ingredient_name.strip():
        return None

    clean_name = ingredient_name.strip().lower()
    canon = INGREDIENT_NORMALIZATION.get(clean_name, clean_name)
    if canon in INGREDIENT_DENSITIES_G_PER_ML:
        return INGREDIENT_DENSITIES_G_PER_ML[canon]

    for key in sorted(INGREDIENT_DENSITIES_G_PER_ML.keys(), key=len, reverse=True):
        if key in clean_name:
            return INGREDIENT_DENSITIES_G_PER_ML[key]

    # Category heuristics based on descriptive terms
    if any(s in clean_name for s in ["powder", "masala", "seeds", "seed", "spice", "mirch"]):
        return 0.60
    if "oil" in clean_name:
        return 0.92
    if any(s in clean_name for s in ["sauce", "juice", "vinegar", "syrup"]):
        return 1.05
    if any(s in clean_name for s in ["milk", "curd", "yogurt", "water", "dahi"]):
        return 1.00

    return None


def convert_cross_dimension_quantity(
    qty: float,
    from_base_unit: str,
    to_base_unit: str,
    ingredient_name: Optional[str] = None,
    original_unit: Optional[str] = None,
) -> Optional[float]:
    """
    Safely convert quantity between base units of different physical dimensions
    (mass: 'g', volume: 'ml', count: 'piece') using ingredient physical heuristics.

    Returns:
        Converted quantity in target base unit, or None if conversion is not possible.
    """
    if qty is None or qty <= 0:
        return None
    if from_base_unit == to_base_unit:
        return qty

    # Count -> Mass ('piece' -> 'g')
    if from_base_unit == "piece" and to_base_unit == "g":
        piece_wt = resolve_ingredient_piece_weight(ingredient_name, original_unit)
        if piece_wt and piece_wt > 0:
            return round(qty * piece_wt, 4)

    # Mass -> Count ('g' -> 'piece')
    elif from_base_unit == "g" and to_base_unit == "piece":
        piece_wt = resolve_ingredient_piece_weight(ingredient_name, original_unit)
        if piece_wt and piece_wt > 0:
            return round(qty / piece_wt, 4)

    # Volume -> Mass ('ml' -> 'g')
    elif from_base_unit == "ml" and to_base_unit == "g":
        density = resolve_ingredient_density(ingredient_name)
        if density and density > 0:
            return round(qty * density, 4)

    # Mass -> Volume ('g' -> 'ml')
    elif from_base_unit == "g" and to_base_unit == "ml":
        density = resolve_ingredient_density(ingredient_name)
        if density and density > 0:
            return round(qty / density, 4)

    # Count -> Volume ('piece' -> 'ml')
    elif from_base_unit == "piece" and to_base_unit == "ml":
        piece_wt = resolve_ingredient_piece_weight(ingredient_name, original_unit)
        density = resolve_ingredient_density(ingredient_name) or 1.0
        if piece_wt and density > 0:
            return round((qty * piece_wt) / density, 4)

    # Volume -> Count ('ml' -> 'piece')
    elif from_base_unit == "ml" and to_base_unit == "piece":
        piece_wt = resolve_ingredient_piece_weight(ingredient_name, original_unit)
        density = resolve_ingredient_density(ingredient_name) or 1.0
        if piece_wt and piece_wt > 0:
            return round((qty * density) / piece_wt, 4)

    return None


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


def calculate_standardized_unit_price(
    price: Optional[float],
    quantity: Optional[float],
    unit_str: Optional[str],
) -> Tuple[Optional[float], Optional[str], Optional[float], Optional[str]]:
    """
    Calculate both base unit price and standard consumer display unit price (e.g. ₹/kg, ₹/L).
    
    Returns:
        (base_unit_price, base_unit, standardized_unit_price, standardized_unit)
        or (None, None, None, None) if calculation is not possible.
    """
    base_price, base_unit = calculate_unit_price(price, quantity, unit_str)
    if base_price is None or base_unit is None:
        return None, None, None, None

    std_unit_info = STANDARDIZED_DISPLAY_UNITS.get(base_unit)
    if not std_unit_info:
        return base_price, base_unit, base_price, base_unit

    std_unit, multiplier = std_unit_info
    std_price = round(base_price * multiplier, 2)
    return base_price, base_unit, std_price, std_unit


def calculate_savings(
    alternative_price: Optional[float],
    reference_price: Optional[float],
    alt_unit_price: Optional[float] = None,
    ref_unit_price: Optional[float] = None,
    alt_quantity: Optional[float] = None,
    ref_quantity: Optional[float] = None,
    alt_unit: Optional[str] = None,
    ref_unit: Optional[str] = None,
    alt_data_source: Optional[str] = None,
    ref_data_source: Optional[str] = None,
    alt_freshness: Optional[str] = None,
    ref_freshness: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Calculate transparent savings between an alternative product and a reference baseline.
    
    Formulas:
        Savings = Reference Price - Alternative Price
        Savings % = (Savings / Reference Price) * 100
        
    Rules:
    - Never combine demo and live prices in a savings calculation.
    - Reference price must be strictly positive (> 0).
    - If package sizes match, savings is computed on package price.
    - If package sizes differ, savings is computed on normalized base unit price.
    - Missing or incompatible quantities omit the savings claim.
    
    Returns:
        (savings_amount, savings_percent, explanation_or_warning)
    """
    if reference_price is None or reference_price <= 0:
        return None, None, "Invalid or nonpositive reference price"
    if alternative_price is None or alternative_price <= 0:
        return None, None, "Invalid or nonpositive alternative price"

    # Source integrity: never compare demo with live prices
    if alt_data_source and ref_data_source:
        if (alt_data_source == "demo" and ref_data_source == "live") or (
            alt_data_source == "live" and ref_data_source == "demo"
        ):
            return None, None, "Cannot compare demo and live sources"

    if alt_freshness and ref_freshness:
        if (alt_freshness == "DEMO" and ref_freshness in ["PROVIDER_LIVE", "LIVE"]) or (
            alt_freshness in ["PROVIDER_LIVE", "LIVE"] and ref_freshness == "DEMO"
        ):
            return None, None, "Cannot compare demo and live sources"

    warning = None
    if alt_freshness and ref_freshness and alt_freshness != ref_freshness:
        warning = f"Mixed freshness: {alt_freshness} vs {ref_freshness}"

    # 1. Equal package size comparison
    if (
        alt_quantity is not None
        and ref_quantity is not None
        and alt_quantity > 0
        and ref_quantity > 0
        and alt_quantity == ref_quantity
        and (alt_unit or "").strip().lower() == (ref_unit or "").strip().lower()
    ):
        diff = round(reference_price - alternative_price, 2)
        pct = round((diff / reference_price) * 100.0, 2)
        return diff, pct, warning

    # 2. Normalized unit price comparison (different package sizes)
    alt_base_qty, alt_base_unit = normalize_unit_and_quantity(alt_quantity, alt_unit)
    ref_base_qty, ref_base_unit = normalize_unit_and_quantity(ref_quantity, ref_unit)

    if (
        alt_base_unit is not None
        and ref_base_unit is not None
        and alt_base_unit == ref_base_unit
        and alt_unit_price is not None
        and ref_unit_price is not None
        and ref_unit_price > 0
        and alt_base_qty is not None
        and alt_base_qty > 0
    ):
        unit_diff = ref_unit_price - alt_unit_price
        pct = round((unit_diff / ref_unit_price) * 100.0, 2)
        diff = round(unit_diff * alt_base_qty, 2)
        return diff, pct, warning

    # 3. Missing or incompatible quantities
    return None, None, "Incompatible or missing package quantities"
