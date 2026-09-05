"""
DishIQ Phase 5.2 — Ingredient Intelligence
Pydantic schemas for the /api/ingredients endpoints.

Fully backward-compatible with Phase 5.1 — all new fields are additive.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class IngredientParseRequest(BaseModel):
    ingredients: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of raw ingredient strings to parse (max 100)",
        examples=[["2 onions", "500 g paneer", "salt to taste"]],
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ParsedIngredientResponse(BaseModel):
    # ── Core (Phase 5.1) ────────────────────────────────────────────────────
    raw_text: str = Field(..., description="Original raw ingredient text")
    canonical_name: str = Field(..., description="Normalised canonical ingredient name")
    quantity: Optional[float] = Field(None, description="Extracted numeric quantity")
    unit: Optional[str] = Field(None, description="Normalised unit of measure (e.g. g, kg, tbsp)")
    preparation_note: Optional[str] = Field(None, description="Detected preparation descriptor")
    optional: bool = Field(False, description="True if ingredient is marked as optional")
    to_taste: bool = Field(False, description="True if ingredient has no fixed quantity ('to taste')")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Parser confidence [0–1]")

    # ── Metadata (Phase 5.2) ────────────────────────────────────────────────
    display_name: str = Field(
        ...,
        description="Cleaned ingredient name before normalisation, title-cased",
    )
    matched_alias: Optional[str] = Field(
        None,
        description="Dictionary alias that triggered normalisation (null if no match)",
    )
    normalization_source: str = Field(
        ...,
        description="How the canonical name was resolved: 'dictionary' | 'unknown'",
    )
    parser_version: str = Field(
        ...,
        description="Version of the ingredient parser used to produce this result",
    )
    category: Optional[str] = Field(
        None,
        description="Ingredient category (vegetable, dairy, grain, spice, …); null for unknown",
    )


class IngredientParseResponse(BaseModel):
    count: int = Field(..., description="Number of ingredients parsed")
    results: List[ParsedIngredientResponse]
