/**
 * DishIQ Phase 5.2 — Ingredient Intelligence
 * Frontend API client for ingredient intelligence endpoints.
 *
 * Endpoints:
 *   POST /api/ingredients/parse
 *   GET  /api/recipes/{recipe_id}/ingredients
 */

import apiClient from './client';
import type { IngredientParseResponse, RecipeIngredientResponse } from '../types/ingredient';

// ---------------------------------------------------------------------------
// POST /api/ingredients/parse
// ---------------------------------------------------------------------------

/**
 * Parse a list of raw ingredient strings through the Ingredient Intelligence engine.
 *
 * @param ingredients - Array of raw ingredient text strings (max 100)
 * @returns Structured ingredient data with normalization metadata
 */
export async function parseIngredients(
  ingredients: string[]
): Promise<IngredientParseResponse> {
  const response = await apiClient.post<IngredientParseResponse>(
    '/ingredients/parse',
    { ingredients }
  );
  return response.data;
}

// ---------------------------------------------------------------------------
// GET /api/recipes/{recipe_id}/ingredients
// ---------------------------------------------------------------------------

/**
 * Retrieve and parse all stored ingredients for a given recipe.
 * The backend fetches raw ingredient strings from the database and passes
 * them through the full Ingredient Intelligence pipeline before returning.
 *
 * @param recipeId - The recipe UUID
 * @returns Structured, normalised ingredient data for the recipe
 */
export async function getRecipeIngredients(
  recipeId: string
): Promise<RecipeIngredientResponse> {
  const response = await apiClient.get<RecipeIngredientResponse>(
    `/recipes/${recipeId}/ingredients`
  );
  return response.data;
}
