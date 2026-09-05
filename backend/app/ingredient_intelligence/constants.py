"""
DishIQ Phase 5.2 — Ingredient Intelligence
Parser-wide constants.

All scoring defaults and version identifiers live here.
Import from this module; do NOT hardcode values inside parser.py.
"""

# ---------------------------------------------------------------------------
# Parser version — bump this when the parsing logic changes materially
# ---------------------------------------------------------------------------
PARSER_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Normalization sources
# ---------------------------------------------------------------------------
NORMALIZATION_SOURCE_DICTIONARY: str = "dictionary"
NORMALIZATION_SOURCE_UNKNOWN: str = "unknown"

# ---------------------------------------------------------------------------
# Confidence scoring defaults
# ---------------------------------------------------------------------------

# Base scores
CONFIDENCE_KNOWN_BASE: float = 0.70      # ingredient is in the known vocabulary
CONFIDENCE_UNKNOWN_BASE: float = 0.45    # ingredient is not in the known vocabulary

# Bonuses (additive, capped at 1.0)
CONFIDENCE_QUANTITY_BONUS: float = 0.15  # a quantity was successfully extracted
CONFIDENCE_UNIT_BONUS: float = 0.10      # a unit was successfully extracted

# Special scores
CONFIDENCE_TO_TASTE: float = 0.80        # "to taste" / "as needed" ingredients
