"""
DishIQ Phase 5.1 — Ingredient Intelligence
Normalization dictionaries for units and ingredients.
These are the single source of truth — edit this file to add new mappings.
"""

from typing import Dict, List, Set

# ---------------------------------------------------------------------------
# UNIT NORMALISATION MAP
# Keys are all lower-case aliases; values are the canonical abbreviated form.
# ---------------------------------------------------------------------------
UNIT_NORMALIZATION: Dict[str, str] = {
    # grams
    "gram": "g",
    "grams": "g",
    "g": "g",
    # kilograms
    "kilogram": "kg",
    "kilograms": "kg",
    "kg": "kg",
    # milligrams
    "milligram": "mg",
    "milligrams": "mg",
    "mg": "mg",
    # millilitres
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "ml": "ml",
    # litres
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
    "l": "l",
    # tablespoons
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "tbsp": "tbsp",
    "tbs": "tbsp",
    "tb": "tbsp",
    # teaspoons
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tsp": "tsp",
    "ts": "tsp",
    # cups
    "cup": "cup",
    "cups": "cup",
    # pieces / count
    "piece": "piece",
    "pieces": "piece",
    "pcs": "piece",
    "pc": "piece",
    # bunch
    "bunch": "bunch",
    "bunches": "bunch",
    # clove
    "clove": "clove",
    "cloves": "clove",
    # head
    "head": "head",
    "heads": "head",
    # pinch
    "pinch": "pinch",
    "pinches": "pinch",
    # handful
    "handful": "handful",
    "handfuls": "handful",
}

# ---------------------------------------------------------------------------
# INGREDIENT NORMALISATION MAP
# Keys are raw/common aliases (lower-cased); values are canonical names.
# ---------------------------------------------------------------------------
INGREDIENT_NORMALIZATION: Dict[str, str] = {
    # Self mappings for canonical ingredients
    "paneer": "paneer",
    "salt": "salt",
    "kesar": "kesar",
    "saffron": "kesar",
    "onion": "onion",
    "tomato": "tomato",
    "coriander": "coriander",
    "butter": "butter",
    "ginger": "ginger",
    "garlic": "garlic",
    "egg": "egg",
    "oil": "oil",
    "spinach": "spinach",
    "potato": "potato",
    "cauliflower": "cauliflower",
    "lemon": "lemon",
    "curd": "curd",
    "cashews": "cashews",
    "pasta": "pasta",
    "cucumber": "cucumber",
    "tortilla": "tortilla",
    "carrot": "carrot",
    "peas": "peas",
    "chana": "chana",
    "toor dal": "toor dal",
    "basmati rice": "basmati rice",
    "chicken breast": "chicken breast",
    "heavy cream": "heavy cream",
    "garam masala": "garam masala",
    "turmeric powder": "turmeric powder",
    "red chili powder": "red chili powder",
    "cumin seeds": "cumin seeds",
    "mustard seeds": "mustard seeds",
    "black pepper": "black pepper",
    "green chili": "green chili",
    "kasuri methi": "kasuri methi",
    "feta cheese": "feta cheese",
    "rice batter": "rice batter",
    "soy sauce": "soy sauce",
    "olive oil": "olive oil",

    # Onion variants
    "tomatoes": "tomato",
    "red onion": "onion",
    "red onions": "onion",
    "white onion": "onion",
    "white onions": "onion",
    "spring onion": "onion",
    "spring onions": "onion",
    "green onion": "onion",
    "green onions": "onion",
    "onions": "onion",
    "shallot": "onion",
    "shallots": "onion",
    # Coriander / cilantro
    "coriander leaves": "coriander",
    "fresh coriander": "coriander",
    "cilantro": "coriander",
    "cilantro leaves": "coriander",
    "dhania": "coriander",
    # Ginger
    "ginger root": "ginger",
    "fresh ginger": "ginger",
    "ginger paste": "ginger",
    # Garlic
    "garlic cloves": "garlic",
    "garlic clove": "garlic",
    "garlic paste": "garlic",
    # Chili
    "green chillies": "green chili",
    "green chilli": "green chili",
    "green chilis": "green chili",
    "green chilies": "green chili",
    "red chilli": "red chili powder",
    "red chillies": "red chili powder",
    "red chili": "red chili powder",
    "chili powder": "red chili powder",
    "chilli powder": "red chili powder",
    # Oil
    "cooking oil": "oil",
    "vegetable oil": "oil",
    "sunflower oil": "oil",
    "refined oil": "oil",
    "olive oils": "olive oil",
    # Turmeric
    "turmeric": "turmeric powder",
    "haldi": "turmeric powder",
    # Cumin
    "jeera": "cumin seeds",
    "cumin": "cumin seeds",
    # Paneer
    "cottage cheese": "paneer",
    "fresh paneer": "paneer",
    # Chicken
    "chicken": "chicken breast",
    "boneless chicken": "chicken breast",
    # Rice
    "rice": "basmati rice",
    "basmati": "basmati rice",
    # Lentils
    "lentils": "toor dal",
    "yellow dal": "toor dal",
    "arhar dal": "toor dal",
    # Chickpeas
    "chickpeas": "chana",
    "kabuli chana": "chana",
    "white chickpeas": "chana",
    # Spinach
    "palak": "spinach",
    "baby spinach": "spinach",
    # Tomato
    "tomatoes": "tomato",
    "cherry tomatoes": "tomato",
    # Potatoes
    "potatoes": "potato",
    "aloo": "potato",
    # Eggs
    "eggs": "egg",
    "large eggs": "egg",
    # Butter
    "unsalted butter": "butter",
    "salted butter": "butter",
    # Cream
    "cream": "heavy cream",
    "fresh cream": "heavy cream",
    "whipping cream": "heavy cream",
    # Salt
    "table salt": "salt",
    "sea salt": "salt",
    "rock salt": "salt",
    "sendha namak": "salt",
    # Pepper
    "pepper": "black pepper",
    "ground pepper": "black pepper",
    "black peppercorns": "black pepper",
    # Garam masala
    "garam masala powder": "garam masala",
    # Mustard seeds
    "mustard": "mustard seeds",
    "black mustard seeds": "mustard seeds",
    "rai": "mustard seeds",
    # Curd / yogurt
    "yogurt": "curd",
    "plain yogurt": "curd",
    "dahi": "curd",
}

# ---------------------------------------------------------------------------
# PREPARATION NOTE KEYWORDS
# Detected in the ingredient text and extracted as preparation_note.
# ---------------------------------------------------------------------------
PREPARATION_NOTES: List[str] = [
    "finely chopped",
    "roughly chopped",
    "coarsely chopped",
    "chopped",
    "finely diced",
    "diced",
    "thinly sliced",
    "thickly sliced",
    "sliced",
    "grated",
    "finely grated",
    "minced",
    "crushed",
    "peeled",
    "peeled and chopped",
    "peeled and diced",
    "peeled and sliced",
    "blanched",
    "boiled",
    "fried",
    "deep fried",
    "roasted",
    "dry roasted",
    "toasted",
    "soaked",
    "overnight soaked",
    "ground",
    "coarsely ground",
    "powdered",
    "pureed",
    "blended",
    "beaten",
    "whisked",
    "melted",
    "softened",
    "boneless",
    "skinless",
    "de-seeded",
    "deseeded",
    "julienned",
    "shredded",
    "torn",
    "halved",
    "quartered",
    "cubed",
    "cut into cubes",
    "roughly pounded",
    "freshly ground",
]

# ---------------------------------------------------------------------------
# "TO TASTE" MARKERS
# Ingredients containing these phrases have no fixed quantity.
# ---------------------------------------------------------------------------
TO_TASTE_MARKERS: List[str] = [
    "to taste",
    "as needed",
    "as required",
    "as per taste",
    "as desired",
]

# ---------------------------------------------------------------------------
# OPTIONAL MARKERS
# Parenthetical or phrase markers indicating an optional ingredient.
# ---------------------------------------------------------------------------
OPTIONAL_MARKERS: List[str] = [
    "optional",
    "if available",
    "if desired",
    "as desired",
    "can be skipped",
]

# ---------------------------------------------------------------------------
# KNOWN INGREDIENT VOCABULARY
# Used for confidence scoring: if canonical name is in this set, confidence
# gets the vocabulary-match bonus.
# ---------------------------------------------------------------------------
KNOWN_INGREDIENTS: Set[str] = {
    "paneer", "tomato", "onion", "green chili", "coriander",
    "butter", "toor dal", "cumin seeds", "turmeric powder", "garam masala",
    "basmati rice", "ginger", "garlic", "chicken breast", "heavy cream",
    "chana", "spinach", "potato", "cauliflower", "rice batter",
    "egg", "oil", "olive oil", "mustard seeds", "red chili powder",
    "salt", "pasta", "cucumber", "feta cheese", "tortilla",
    "bell pepper", "soy sauce", "carrot", "peas", "lemon",
    "curd", "cashews", "coriander powder", "black pepper", "kasuri methi",
    "kesar",
}


