/**
 * DishIQ Phase 5.2 — Ingredient Intelligence
 * TypeScript types for the Ingredient Intelligence engine.
 *
 * These types mirror the backend Pydantic schemas in
 * backend/app/schemas/ingredient.py and are reusable across all future phases.
 */

// ---------------------------------------------------------------------------
// Category labels (mirrors VALID_CATEGORIES in backend categories.py)
// ---------------------------------------------------------------------------
export type IngredientCategory =
  | 'vegetable'
  | 'fruit'
  | 'grain'
  | 'legume'
  | 'dairy'
  | 'meat'
  | 'seafood'
  | 'egg'
  | 'spice'
  | 'seasoning'
  | 'oil'
  | 'herb'
  | 'nut'
  | 'sweetener'
  | 'condiment'
  | 'bakery'
  | 'beverage';

// ---------------------------------------------------------------------------
// Normalisation source
// ---------------------------------------------------------------------------
export type NormalizationSource = 'dictionary' | 'unknown';

// ---------------------------------------------------------------------------
// Single parsed ingredient (mirrors ParsedIngredientResponse)
// ---------------------------------------------------------------------------
export interface ParsedIngredient {
  /** Original raw ingredient text submitted to the parser */
  raw_text: string;
  /** Cleaned ingredient name before normalisation, title-cased */
  display_name: string;
  /** Normalised canonical ingredient name */
  canonical_name: string;
  /** Ingredient category; null for unknown ingredients */
  category: IngredientCategory | null;
  /** Extracted numeric quantity; null if not found */
  quantity: number | null;
  /** Normalised unit of measure (e.g. g, kg, tbsp); null if not found */
  unit: string | null;
  /** Detected preparation descriptor (e.g. "finely chopped"); null if absent */
  preparation_note: string | null;
  /** True if the ingredient is marked as optional */
  optional: boolean;
  /** True if the ingredient has no fixed quantity (e.g. "to taste") */
  to_taste: boolean;
  /** Parser confidence in [0, 1] */
  confidence_score: number;
  /** Dictionary alias that triggered normalisation; null for unknown */
  matched_alias: string | null;
  /** How the canonical name was resolved */
  normalization_source: NormalizationSource;
  /** Version of the ingredient parser */
  parser_version: string;
}

// ---------------------------------------------------------------------------
// API response shapes
// ---------------------------------------------------------------------------

/** Response from POST /api/ingredients/parse */
export interface IngredientParseResponse {
  count: number;
  results: ParsedIngredient[];
}

/** Response from GET /api/recipes/{id}/ingredients */
export type RecipeIngredientResponse = IngredientParseResponse;
