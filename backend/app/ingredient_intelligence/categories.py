"""
DishIQ Phase 5.2 — Ingredient Intelligence
Ingredient category mapping.

Maps canonical ingredient names to high-level category labels.
Edit this file to add / change category assignments.
Unknown ingredients return None in the parser.

Prepared for Phase 6 (Grocery Product Matching) — not yet used for matching.
"""

from typing import Optional, Set, Dict

# ---------------------------------------------------------------------------
# Supported category labels
# ---------------------------------------------------------------------------
VALID_CATEGORIES: Set[str] = {
    "vegetable",
    "fruit",
    "grain",
    "legume",
    "dairy",
    "meat",
    "seafood",
    "egg",
    "spice",
    "seasoning",
    "oil",
    "herb",
    "nut",
    "sweetener",
    "condiment",
    "bakery",
    "beverage",
}

# ---------------------------------------------------------------------------
# Category dictionary
# Keys must be canonical ingredient names (lower-case, matching KNOWN_INGREDIENTS
# and the values in INGREDIENT_NORMALIZATION).
# ---------------------------------------------------------------------------
INGREDIENT_CATEGORIES: Dict[str, str] = {
    # ── Vegetables ──────────────────────────────────────────────────────────
    "onion": "vegetable",
    "tomato": "vegetable",
    "potato": "vegetable",
    "cauliflower": "vegetable",
    "spinach": "vegetable",
    "carrot": "vegetable",
    "peas": "vegetable",
    "bell pepper": "vegetable",
    "green chili": "vegetable",
    "cucumber": "vegetable",
    "ginger": "vegetable",
    "garlic": "vegetable",
    "eggplant": "vegetable",

    # ── Herbs ───────────────────────────────────────────────────────────────
    "coriander": "herb",
    "kasuri methi": "herb",

    # ── Fruits ──────────────────────────────────────────────────────────────
    "lemon": "fruit",

    # ── Grains & Pulses (Grain) ─────────────────────────────────────────────
    "basmati rice": "grain",
    "pasta": "grain",
    "tortilla": "grain",
    "rice batter": "grain",
    "all-purpose flour": "grain",
    "wheat flour": "grain",
    "rice flour": "grain",
    "cornstarch": "grain",

    # ── Legumes ─────────────────────────────────────────────────────────────
    "toor dal": "legume",
    "chana": "legume",
    "besan": "legume",

    # ── Dairy ───────────────────────────────────────────────────────────────
    "paneer": "dairy",
    "butter": "dairy",
    "heavy cream": "dairy",
    "curd": "dairy",
    "feta cheese": "dairy",
    "milk": "dairy",
    "buttermilk": "dairy",
    "almond milk": "dairy",

    # ── Meat ────────────────────────────────────────────────────────────────
    "chicken breast": "meat",

    # ── Egg ─────────────────────────────────────────────────────────────────
    "egg": "egg",

    # ── Spices ──────────────────────────────────────────────────────────────
    "turmeric powder": "spice",
    "garam masala": "spice",
    "cumin seeds": "spice",
    "cumin powder": "spice",
    "mustard seeds": "spice",
    "red chili powder": "spice",
    "coriander powder": "spice",
    "coriander seeds": "spice",
    "black pepper": "spice",
    "kesar": "spice",
    "clove": "spice",
    "ground clove": "spice",
    "ginger powder": "spice",

    # ── Seasoning & Condiments ───────────────────────────────────────────────
    "salt": "seasoning",
    "soy sauce": "condiment",
    "coconut milk": "beverage",
    "soy milk": "beverage",

    # ── Oils ────────────────────────────────────────────────────────────────
    "oil": "oil",
    "olive oil": "oil",
    "cooking oil": "oil",
    "mustard oil": "oil",
    "coconut oil": "oil",
    "sesame oil": "oil",

    # ── Nuts & Seeds ────────────────────────────────────────────────────────
    "cashews": "nut",
    "peanut butter": "nut",
}


def get_category(canonical_name: str) -> Optional[str]:
    """
    Look up the category for a canonical ingredient name.
    Returns None for unknown ingredients.
    """
    return INGREDIENT_CATEGORIES.get(canonical_name.strip().lower())

