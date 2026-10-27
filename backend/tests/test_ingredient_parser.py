"""
DishIQ Phase 5.2 — Ingredient Intelligence
Comprehensive parser test suite — 55+ tests covering all pipeline stages
and Phase 5.2 metadata (display_name, matched_alias, normalization_source,
parser_version, category).

Run with:
    cd d:\\DishIQ
    python -m pytest backend/tests/test_ingredient_parser.py -v
"""
from __future__ import annotations

import math
import sys
import os

# Ensure repository root is accessible for import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.ingredient_intelligence.parser import (
    parse_ingredient,
    clean_text,
    detect_to_taste,
    detect_optional,
    extract_quantity,
    extract_unit,
    extract_preparation_note,
    normalize_ingredient,
    compute_confidence,
    resolve_fractions,
)


# ===========================================================================
# Helper
# ===========================================================================

def parsed(raw: str):
    """Shorthand to parse a single ingredient."""
    return parse_ingredient(raw)


# ===========================================================================
# Stage 1 — Text Cleaning
# ===========================================================================

class TestTextCleaning:
    def test_strips_leading_trailing_whitespace(self):
        assert clean_text("  paneer  ") == "paneer"

    def test_collapses_internal_whitespace(self):
        assert clean_text("2   onions   finely  chopped") == "2 onions finely chopped"

    def test_replaces_em_dash_with_hyphen(self):
        result = clean_text("1\u2014cup rice")
        assert "\u2014" not in result

    def test_handles_empty_string(self):
        assert clean_text("") == ""


# ===========================================================================
# Stage 2 — To-Taste Detection
# ===========================================================================

class TestToTasteDetection:
    def test_salt_to_taste(self):
        is_tt, _ = detect_to_taste("salt to taste")
        assert is_tt is True

    def test_as_needed(self):
        is_tt, _ = detect_to_taste("pepper as needed")
        assert is_tt is True

    def test_as_required(self):
        is_tt, _ = detect_to_taste("oil as required")
        assert is_tt is True

    def test_no_to_taste(self):
        is_tt, _ = detect_to_taste("2 onions finely chopped")
        assert is_tt is False


# ===========================================================================
# Stage 3 — Optional Detection
# ===========================================================================

class TestOptionalDetection:
    def test_parenthetical_optional(self):
        is_opt, _ = detect_optional("fresh coriander (optional)")
        assert is_opt is True

    def test_parenthetical_if_available(self):
        is_opt, _ = detect_optional("saffron (if available)")
        assert is_opt is True

    def test_not_optional(self):
        is_opt, _ = detect_optional("2 cups basmati rice")
        assert is_opt is False

    def test_parenthetical_text_removed(self):
        _, cleaned = detect_optional("coriander leaves (optional)")
        assert "(optional)" not in cleaned


# ===========================================================================
# Stage 4 — Fraction Resolution
# ===========================================================================

class TestFractionResolution:
    def test_unicode_half(self):
        val, _ = resolve_fractions("½ cup milk")
        assert math.isclose(val, 0.5, abs_tol=1e-6)

    def test_unicode_three_quarters(self):
        val, _ = resolve_fractions("¾ tsp turmeric")
        assert math.isclose(val, 0.75, abs_tol=1e-6)

    def test_mixed_number(self):
        val, _ = resolve_fractions("1½ cups basmati rice")
        assert math.isclose(val, 1.5, abs_tol=1e-6)

    def test_text_fraction_half(self):
        val, _ = resolve_fractions("1/2 tsp salt")
        assert math.isclose(val, 0.5, abs_tol=1e-6)

    def test_text_fraction_three_quarters(self):
        val, _ = resolve_fractions("3/4 cup curd")
        assert math.isclose(val, 0.75, abs_tol=1e-6)

    def test_no_fraction_returns_none(self):
        val, _ = resolve_fractions("salt to taste")
        assert val is None


# ===========================================================================
# Stage 5 — Quantity Extraction
# ===========================================================================

class TestQuantityExtraction:
    def test_whole_number(self):
        qty, _ = extract_quantity("2 onions")
        assert qty == 2.0

    def test_decimal(self):
        qty, _ = extract_quantity("0.5 kg chicken")
        assert math.isclose(qty, 0.5, abs_tol=1e-6)

    def test_large_number(self):
        qty, _ = extract_quantity("500 g paneer")
        assert qty == 500.0

    def test_missing_quantity_returns_none(self):
        qty, _ = extract_quantity("salt")
        assert qty is None

    def test_to_taste_no_quantity(self):
        qty, _ = extract_quantity("salt to taste")
        assert qty is None


# ===========================================================================
# Stage 6 — Unit Extraction and Normalisation
# ===========================================================================

class TestUnitExtraction:
    def test_grams_abbreviated(self):
        unit, _ = extract_unit("g paneer")
        assert unit == "g"

    def test_grams_full_word(self):
        unit, _ = extract_unit("grams paneer")
        assert unit == "g"

    def test_kilograms(self):
        unit, _ = extract_unit("kg chicken")
        assert unit == "kg"

    def test_tablespoon(self):
        unit, _ = extract_unit("tbsp oil")
        assert unit == "tbsp"

    def test_tablespoon_full(self):
        unit, _ = extract_unit("tablespoon oil")
        assert unit == "tbsp"

    def test_teaspoon(self):
        unit, _ = extract_unit("tsp cumin seeds")
        assert unit == "tsp"

    def test_cup(self):
        unit, _ = extract_unit("cup curd")
        assert unit == "cup"

    def test_cups(self):
        unit, _ = extract_unit("cups basmati rice")
        assert unit == "cup"

    def test_no_unit(self):
        unit, _ = extract_unit("onions finely chopped")
        assert unit is None


# ===========================================================================
# Stage 7 — Preparation Note Extraction
# ===========================================================================

class TestPreparationNoteExtraction:
    def test_finely_chopped(self):
        note, _ = extract_preparation_note("onions finely chopped")
        assert note == "finely chopped"

    def test_diced(self):
        note, _ = extract_preparation_note("tomatoes diced")
        assert note == "diced"

    def test_grated(self):
        note, _ = extract_preparation_note("ginger grated")
        assert note == "grated"

    def test_crushed(self):
        note, _ = extract_preparation_note("garlic crushed")
        assert note == "crushed"

    def test_boneless(self):
        note, _ = extract_preparation_note("chicken boneless")
        assert note == "boneless"

    def test_no_prep_note(self):
        note, _ = extract_preparation_note("basmati rice")
        assert note is None


# ===========================================================================
# Stage 8 — Ingredient Normalisation
# ===========================================================================

class TestIngredientNormalization:
    # normalize_ingredient() now returns a NormResult namedtuple; use .canonical_name
    def test_red_onions_to_onion(self):
        assert normalize_ingredient("red onions").canonical_name == "onion"

    def test_tomatoes_to_tomato(self):
        assert normalize_ingredient("tomatoes").canonical_name == "tomato"

    def test_coriander_leaves_to_coriander(self):
        assert normalize_ingredient("coriander leaves").canonical_name == "coriander"

    def test_cooking_oil_to_oil(self):
        assert normalize_ingredient("cooking oil").canonical_name == "oil"

    def test_unknown_returns_as_is(self):
        assert normalize_ingredient("mystery spice").canonical_name == "mystery spice"

    def test_case_insensitive(self):
        assert normalize_ingredient("Tomatoes".lower()).canonical_name == "tomato"

    # Phase 5.2 — NormResult fields
    def test_matched_alias_present_on_dict_hit(self):
        result = normalize_ingredient("red onions")
        assert result.matched_alias is not None
        assert result.normalization_source == "dictionary"

    def test_normalization_source_unknown_for_unknown(self):
        result = normalize_ingredient("mystery herb xyz")
        assert result.normalization_source == "unknown"
        assert result.matched_alias is None

    def test_matched_alias_value(self):
        result = normalize_ingredient("coriander leaves")
        assert result.matched_alias == "coriander leaves"


# ===========================================================================
# Full Parse Pipeline Tests
# ===========================================================================

class TestFullParsePipeline:
    def test_whole_number_quantity_and_unit(self):
        r = parsed("500 g paneer")
        assert r.quantity == 500.0
        assert r.unit == "g"
        assert r.canonical_name == "paneer"
        assert r.confidence_score > 0.7

    def test_tablespoon_oil(self):
        r = parsed("2 tbsp olive oil")
        assert r.quantity == 2.0
        assert r.unit == "tbsp"
        assert "olive oil" in r.canonical_name

    def test_salt_to_taste(self):
        r = parsed("salt to taste")
        assert r.to_taste is True
        assert r.quantity is None
        assert r.canonical_name == "salt"
        assert math.isclose(r.confidence_score, 0.80, abs_tol=1e-6)

    def test_optional_ingredient(self):
        r = parsed("fresh coriander leaves (optional)")
        assert r.optional is True
        assert r.canonical_name == "coriander"

    def test_fraction_cup_basmati_rice(self):
        r = parsed("1½ cups basmati rice")
        assert math.isclose(r.quantity, 1.5, abs_tol=1e-6)
        assert r.unit == "cup"
        assert "basmati rice" in r.canonical_name

    def test_preparation_note_extracted(self):
        r = parsed("2 large onions, finely chopped")
        assert r.preparation_note == "finely chopped"
        assert r.canonical_name == "onion"

    def test_boneless_chicken(self):
        r = parsed("500 g boneless chicken")
        assert r.quantity == 500.0
        assert r.unit == "g"
        assert r.preparation_note == "boneless"

    def test_unknown_ingredient_low_confidence(self):
        r = parsed("3 sprigs dragon weed")
        assert r.confidence_score < 0.7

    def test_multiword_ingredient_garlic(self):
        r = parsed("4 garlic cloves, crushed")
        assert r.canonical_name == "garlic"
        assert r.preparation_note == "crushed"

    def test_unicode_fraction(self):
        r = parsed("¼ tsp turmeric powder")
        assert math.isclose(r.quantity, 0.25, abs_tol=1e-6)
        assert r.unit == "tsp"

    def test_text_fraction(self):
        r = parsed("1/2 tsp garam masala")
        assert math.isclose(r.quantity, 0.5, abs_tol=1e-6)
        assert r.unit == "tsp"

    def test_decimal_quantity(self):
        r = parsed("0.5 kg chicken breast")
        assert math.isclose(r.quantity, 0.5, abs_tol=1e-6)
        assert r.unit == "kg"

    def test_no_quantity_unknown(self):
        r = parsed("a pinch of kesar")
        assert r.canonical_name == "kesar"
        assert r.quantity is None
        assert r.unit is None

    def test_confidence_known_ingredient_with_qty_and_unit(self):
        r = parsed("200 g paneer")
        assert r.confidence_score >= 0.90

    def test_grams_full_word_normalised(self):
        r = parsed("200 grams paneer")
        assert r.unit == "g"

    def test_kilograms_normalised(self):
        r = parsed("1 kg basmati rice")
        assert r.unit == "kg"
        assert "basmati rice" in r.canonical_name

    def test_egg_normalised(self):
        r = parsed("6 eggs")
        assert r.canonical_name == "egg"

    def test_red_onion_normalised(self):
        r = parsed("1 red onion, diced")
        assert r.canonical_name == "onion"
        assert r.preparation_note == "diced"

    def test_raw_text_preserved(self):
        raw = "2 onions finely chopped"
        r = parsed(raw)
        assert r.raw_text == raw

    def test_to_taste_no_unit(self):
        r = parsed("black pepper to taste")
        assert r.to_taste is True
        assert r.unit is None


# ===========================================================================
# API Endpoint Tests
# ===========================================================================

class TestIngredientParseAPI:
    """Integration tests using the FastAPI TestClient."""

    def test_parse_endpoint_basic(self, client):
        response = client.post(
            "/api/ingredients/parse",
            json={"ingredients": ["2 onions", "500 g paneer"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        results = data["results"]
        assert results[0]["canonical_name"] == "onion"
        assert results[1]["canonical_name"] == "paneer"

    def test_parse_endpoint_salt_to_taste(self, client):
        response = client.post(
            "/api/ingredients/parse",
            json={"ingredients": ["salt to taste"]}
        )
        assert response.status_code == 200
        data = response.json()
        r = data["results"][0]
        assert r["to_taste"] is True
        assert r["quantity"] is None

    def test_parse_endpoint_optional(self, client):
        response = client.post(
            "/api/ingredients/parse",
            json={"ingredients": ["fresh coriander (optional)"]}
        )
        assert response.status_code == 200
        r = response.json()["results"][0]
        assert r["optional"] is True
        assert r["canonical_name"] == "coriander"

    def test_parse_endpoint_fraction(self, client):
        response = client.post(
            "/api/ingredients/parse",
            json={"ingredients": ["1/2 tsp turmeric powder"]}
        )
        assert response.status_code == 200
        r = response.json()["results"][0]
        assert abs(r["quantity"] - 0.5) < 0.01
        assert r["unit"] == "tsp"

    def test_parse_endpoint_unit_normalization(self, client):
        response = client.post(
            "/api/ingredients/parse",
            json={"ingredients": ["200 grams paneer", "1 tablespoon oil"]}
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert results[0]["unit"] == "g"
        assert results[1]["unit"] == "tbsp"

    def test_parse_endpoint_empty_list_rejected(self, client):
        response = client.post(
            "/api/ingredients/parse",
            json={"ingredients": []}
        )
        assert response.status_code == 422

    def test_recipe_ingredients_endpoint_valid(self, client):
        # First, get a valid recipe ID from the seeded data
        recipes_resp = client.get("/api/recipes/search?page_size=1")
        assert recipes_resp.status_code == 200
        items = recipes_resp.json()["items"]
        if items:
            recipe_id = items[0]["id"]
            resp = client.get(f"/api/recipes/{recipe_id}/ingredients")
            assert resp.status_code == 200
            data = resp.json()
            assert "count" in data
            assert "results" in data
            assert data["count"] >= 0

    def test_recipe_ingredients_endpoint_not_found(self, client):
        response = client.get("/api/recipes/nonexistent_id_xyz/ingredients")
        assert response.status_code == 404

    def test_parse_endpoint_preparation_note_in_response(self, client):
        response = client.post(
            "/api/ingredients/parse",
            json={"ingredients": ["2 large onions, finely chopped"]}
        )
        assert response.status_code == 200
        r = response.json()["results"][0]
        assert r["preparation_note"] == "finely chopped"

    def test_parse_endpoint_confidence_scores_present(self, client):
        response = client.post(
            "/api/ingredients/parse",
            json={"ingredients": ["500 g paneer", "mystery herb xyz"]}
        )
        assert response.status_code == 200
        results = response.json()["results"]
        for r in results:
            assert 0.0 <= r["confidence_score"] <= 1.0
        assert results[0]["confidence_score"] > results[1]["confidence_score"]


# ===========================================================================
# Phase 5.2 — Metadata Fields
# ===========================================================================

class TestPhase52Metadata:
    """Tests for display_name, matched_alias, normalization_source,
    parser_version, and category fields added in Phase 5.2."""

    def test_display_name_is_title_cased(self):
        r = parse_ingredient("large onions")
        assert r.display_name == "Large Onions"

    def test_display_name_preserved_before_normalization(self):
        r = parse_ingredient("red onions")
        # display_name is the raw name fragment, NOT the canonical
        assert r.canonical_name == "onion"   # normalised
        assert r.display_name != "Onion"     # NOT yet normalised

    def test_matched_alias_on_known_ingredient(self):
        r = parse_ingredient("tomatoes")
        assert r.matched_alias is not None
        assert r.normalization_source == "dictionary"

    def test_matched_alias_none_for_unknown(self):
        r = parse_ingredient("dragon root xyz")
        assert r.matched_alias is None
        assert r.normalization_source == "unknown"

    def test_parser_version_present(self):
        r = parse_ingredient("2 onions")
        assert r.parser_version == "1.0"

    def test_parser_version_consistent(self):
        from app.ingredient_intelligence.constants import PARSER_VERSION
        r = parse_ingredient("500 g paneer")
        assert r.parser_version == PARSER_VERSION

    def test_category_vegetable_for_onion(self):
        r = parse_ingredient("2 onions")
        assert r.category == "vegetable"

    def test_category_dairy_for_paneer(self):
        r = parse_ingredient("500 g paneer")
        assert r.category == "dairy"

    def test_category_spice_for_turmeric(self):
        r = parse_ingredient("1/4 tsp turmeric powder")
        assert r.category == "spice"

    def test_category_seasoning_for_salt(self):
        r = parse_ingredient("salt to taste")
        assert r.category == "seasoning"

    def test_category_null_for_unknown(self):
        r = parse_ingredient("dragon root xyz")
        assert r.category is None

    def test_category_grain_for_rice(self):
        r = parse_ingredient("1 cup basmati rice")
        assert r.category == "grain"

    def test_category_meat_for_chicken(self):
        r = parse_ingredient("300 g chicken breast")
        assert r.category == "meat"

    def test_category_herb_for_coriander(self):
        r = parse_ingredient("fresh coriander leaves")
        assert r.category == "herb"

    def test_category_oil_for_olive_oil(self):
        r = parse_ingredient("2 tbsp olive oil")
        assert r.category == "oil"

    def test_paneer_normalization_dictionary(self):
        r = parse_ingredient("paneer")
        assert r.canonical_name == "paneer"
        assert r.normalization_source == "dictionary"
        assert r.matched_alias == "paneer"

    def test_salt_to_taste_canonical_and_category(self):
        r = parse_ingredient("salt to taste")
        assert r.canonical_name == "salt"
        assert r.to_taste is True
        assert r.category == "seasoning"
        assert r.normalization_source == "dictionary"

    def test_unicode_mixed_fraction_1_and_half(self):
        r = parse_ingredient("1½ cups basmati rice")
        assert math.isclose(r.quantity, 1.5, abs_tol=1e-6)
        assert r.unit == "cup"
        assert r.canonical_name == "basmati rice"

    def test_unicode_standalone_fraction_quarter(self):
        r = parse_ingredient("¼ tsp turmeric powder")
        assert math.isclose(r.quantity, 0.25, abs_tol=1e-6)
        assert r.unit == "tsp"

    def test_a_pinch_of_kesar_handling(self):
        r = parse_ingredient("a pinch of kesar")
        assert r.canonical_name == "kesar"
        assert r.quantity is None
        assert r.unit is None
        assert r.category == "spice"


# ===========================================================================
# Phase 5.2 — API Metadata Fields
# ===========================================================================

class TestPhase52APIMetadata:
    """Verify the new metadata fields are present in the API response."""

    def test_api_returns_display_name(self, client):
        resp = client.post("/api/ingredients/parse", json={"ingredients": ["red onions"]})
        assert resp.status_code == 200
        r = resp.json()["results"][0]
        assert "display_name" in r
        assert len(r["display_name"]) > 0

    def test_api_returns_matched_alias(self, client):
        resp = client.post("/api/ingredients/parse", json={"ingredients": ["tomatoes"]})
        assert resp.status_code == 200
        r = resp.json()["results"][0]
        assert "matched_alias" in r
        assert r["matched_alias"] is not None

    def test_api_returns_normalization_source_dictionary(self, client):
        resp = client.post("/api/ingredients/parse", json={"ingredients": ["paneer"]})
        assert resp.status_code == 200
        r = resp.json()["results"][0]
        assert r["normalization_source"] == "dictionary"

    def test_api_returns_normalization_source_unknown(self, client):
        resp = client.post("/api/ingredients/parse", json={"ingredients": ["mystery bark"]})
        assert resp.status_code == 200
        r = resp.json()["results"][0]
        assert r["normalization_source"] == "unknown"

    def test_api_returns_parser_version(self, client):
        resp = client.post("/api/ingredients/parse", json={"ingredients": ["2 eggs"]})
        assert resp.status_code == 200
        r = resp.json()["results"][0]
        assert r["parser_version"] == "1.0"

    def test_api_returns_category_for_known(self, client):
        resp = client.post("/api/ingredients/parse", json={"ingredients": ["500 g paneer"]})
        assert resp.status_code == 200
        r = resp.json()["results"][0]
        assert r["category"] == "dairy"

    def test_api_returns_null_category_for_unknown(self, client):
        resp = client.post("/api/ingredients/parse", json={"ingredients": ["alien root"]})
        assert resp.status_code == 200
        r = resp.json()["results"][0]
        assert r["category"] is None


# ===========================================================================
# Phase 5 — Mixed Fractions, Word Boundaries & Distinct Concept Preservation
# ===========================================================================

class TestPhase5DistinctIngredientsAndFractions:
    def test_text_mixed_fractions(self):
        r1 = parse_ingredient("1 1/2 cups flour")
        assert math.isclose(r1.quantity, 1.5, abs_tol=1e-6)
        assert r1.unit == "cup"
        assert r1.canonical_name == "flour"

        r2 = parse_ingredient("1-1/2 cups maida")
        assert math.isclose(r2.quantity, 1.5, abs_tol=1e-6)
        assert r2.unit == "cup"
        assert r2.canonical_name == "all-purpose flour"

    def test_leading_of_stripped(self):
        r = parse_ingredient("1 cup of milk")
        assert r.quantity == 1.0
        assert r.unit == "cup"
        assert r.canonical_name == "milk"

    def test_eggplant_distinct_from_egg(self):
        r = parse_ingredient("1 medium eggplant")
        assert r.canonical_name == "eggplant"
        assert r.canonical_name != "egg"
        assert r.category == "vegetable"

    def test_buttermilk_distinct_from_butter(self):
        r = parse_ingredient("2 cups buttermilk")
        assert r.canonical_name == "buttermilk"
        assert r.canonical_name != "butter"
        assert r.category == "dairy"

    def test_peanut_butter_distinct_from_butter(self):
        r = parse_ingredient("2 tbsp peanut butter")
        assert r.canonical_name == "peanut butter"
        assert r.canonical_name != "butter"
        assert r.category == "nut"

    def test_coconut_milk_distinct_from_dairy_milk(self):
        r = parse_ingredient("1 cup coconut milk")
        assert r.canonical_name == "coconut milk"
        assert r.canonical_name != "milk"

    def test_mustard_oil_distinct_from_mustard_seeds(self):
        r = parse_ingredient("2 tbsp mustard oil")
        assert r.canonical_name == "mustard oil"
        assert r.canonical_name != "mustard seeds"
        assert r.category == "oil"

    def test_coriander_seeds_distinct_from_coriander_leaves(self):
        r = parse_ingredient("1 tsp coriander seeds")
        assert r.canonical_name == "coriander seeds"
        assert r.category == "spice"

    def test_ground_spices_distinct(self):
        r1 = parse_ingredient("1 tsp cumin powder")
        assert r1.canonical_name == "cumin powder"
        assert r1.category == "spice"

        r2 = parse_ingredient("1/2 tsp ginger powder")
        assert r2.canonical_name == "ginger powder"
        assert r2.category == "spice"

    def test_cloves_distinction(self):
        # As unit of garlic
        r_garlic = parse_ingredient("4 cloves of garlic")
        assert r_garlic.quantity == 4.0
        assert r_garlic.unit == "clove"
        assert r_garlic.canonical_name == "garlic"

        # As the whole spice
        r_clove = parse_ingredient("4 cloves")
        assert r_clove.quantity == 4.0
        assert r_clove.canonical_name == "clove"
        assert r_clove.category == "spice"

        # Ground cloves: note extracted as prep note, canonical resolved to clove
        r_ground = parse_ingredient("1/4 tsp ground cloves")
        assert r_ground.unit == "tsp"
        assert r_ground.canonical_name == "clove"
        assert r_ground.preparation_note == "ground"
        assert r_ground.category == "spice"
