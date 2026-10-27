"""
DishIQ Ingredient Intelligence Package.
"""
from app.ingredient_intelligence.parser import (
    parse_ingredient,
    parse_ingredients,
    ParsedIngredient,
    NormResult,
    clean_text,
    detect_to_taste,
    detect_optional,
    extract_quantity,
    extract_unit,
    extract_preparation_note,
    normalize_ingredient,
    compute_confidence,
)
from app.ingredient_intelligence.units import (
    UnitDimension,
    normalize_unit,
    get_unit_dimension,
    are_units_compatible,
    convert_quantity,
    format_quantity_and_unit,
)
from app.ingredient_intelligence.categories import get_category
from app.ingredient_intelligence.constants import PARSER_VERSION

__all__ = [
    "parse_ingredient",
    "parse_ingredients",
    "ParsedIngredient",
    "NormResult",
    "clean_text",
    "detect_to_taste",
    "detect_optional",
    "extract_quantity",
    "extract_unit",
    "extract_preparation_note",
    "normalize_ingredient",
    "compute_confidence",
    "UnitDimension",
    "normalize_unit",
    "get_unit_dimension",
    "are_units_compatible",
    "convert_quantity",
    "format_quantity_and_unit",
    "get_category",
    "PARSER_VERSION",
]
