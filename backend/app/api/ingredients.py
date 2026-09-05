"""
DishIQ Phase 5.2 — Ingredient Intelligence
API endpoints:
  POST /api/ingredients/parse
  GET  /api/recipes/{recipe_id}/ingredients
"""
from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ingredient_intelligence.parser import parse_ingredients, ParsedIngredient
from app.models.recipe import Recipe, RecipeIngredient
from app.schemas.ingredient import (
    IngredientParseRequest,
    IngredientParseResponse,
    ParsedIngredientResponse,
)

router = APIRouter(tags=["Ingredient Intelligence"])


def _to_response(p: ParsedIngredient) -> ParsedIngredientResponse:
    return ParsedIngredientResponse(
        # Phase 5.1 fields
        raw_text=p.raw_text,
        canonical_name=p.canonical_name,
        quantity=p.quantity,
        unit=p.unit,
        preparation_note=p.preparation_note,
        optional=p.optional,
        to_taste=p.to_taste,
        confidence_score=p.confidence_score,
        # Phase 5.2 fields
        display_name=p.display_name,
        matched_alias=p.matched_alias,
        normalization_source=p.normalization_source,
        parser_version=p.parser_version,
        category=p.category,
    )


# ---------------------------------------------------------------------------
# POST /api/ingredients/parse
# ---------------------------------------------------------------------------

@router.post(
    "/ingredients/parse",
    response_model=IngredientParseResponse,
    summary="Parse Raw Ingredient Strings",
    description=(
        "Submit a list of raw ingredient strings and receive structured, "
        "normalised ingredient data including quantity, unit, preparation note, "
        "category, optional flag, normalization metadata, and parser confidence score."
    ),
)
def parse_ingredient_list(
    body: IngredientParseRequest,
) -> IngredientParseResponse:
    parsed = parse_ingredients(body.ingredients)
    results = [_to_response(p) for p in parsed]
    return IngredientParseResponse(count=len(results), results=results)


# ---------------------------------------------------------------------------
# GET /api/recipes/{recipe_id}/ingredients
# ---------------------------------------------------------------------------

@router.get(
    "/recipes/{recipe_id}/ingredients",
    response_model=IngredientParseResponse,
    summary="Get Normalised Ingredients for a Recipe",
    description=(
        "Retrieve the stored raw ingredient strings for a recipe and return "
        "them fully parsed through the Ingredient Intelligence engine, "
        "including Phase 5.2 metadata (category, display_name, matched_alias, etc.)."
    ),
)
def get_recipe_ingredients(
    recipe_id: str,
    db: Session = Depends(get_db),
) -> IngredientParseResponse:
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe '{recipe_id}' not found.",
        )

    rec_ingredients: List[RecipeIngredient] = (
        db.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )


    raw_texts = [ri.raw_text for ri in rec_ingredients if ri.raw_text]
    if not raw_texts:
        return IngredientParseResponse(count=0, results=[])

    parsed = parse_ingredients(raw_texts)
    results = [_to_response(p) for p in parsed]
    return IngredientParseResponse(count=len(results), results=results)
