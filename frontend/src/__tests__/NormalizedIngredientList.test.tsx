/**
 * DishIQ Phase 5.2 — Ingredient Intelligence
 * Tests for NormalizedIngredientList component.
 *
 * Covers loading, error, empty, and populated states using React Query mocks.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NormalizedIngredientList } from '../components/recipe/NormalizedIngredientList';
import type { ParsedIngredient, RecipeIngredientResponse } from '../types/ingredient';

// ---------------------------------------------------------------------------
// Mock the API module
// ---------------------------------------------------------------------------
vi.mock('../api/ingredients', () => ({
  getRecipeIngredients: vi.fn(),
}));

import { getRecipeIngredients } from '../api/ingredients';
const mockedGetRecipeIngredients = vi.mocked(getRecipeIngredients);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTestIngredient(overrides: Partial<ParsedIngredient> = {}): ParsedIngredient {
  return {
    raw_text: '500 g paneer',
    display_name: 'Paneer',
    canonical_name: 'paneer',
    category: 'dairy',
    quantity: 500,
    unit: 'g',
    preparation_note: null,
    optional: false,
    to_taste: false,
    confidence_score: 0.95,
    matched_alias: 'paneer',
    normalization_source: 'dictionary',
    parser_version: '1.0',
    ...overrides,
  };
}

function makeTestResponse(results: ParsedIngredient[]): RecipeIngredientResponse {
  return { count: results.length, results };
}

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,         // no retry in tests
        gcTime: Infinity,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

describe('NormalizedIngredientList — loading state', () => {
  it('shows loading indicator while fetching', async () => {
    // Never resolves → stays loading
    mockedGetRecipeIngredients.mockReturnValue(new Promise(() => {}));
    renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );
    expect(screen.getByText(/Analysing ingredients/i)).toBeInTheDocument();
  });
});

describe('NormalizedIngredientList — error state', () => {
  it('shows error message on API failure', async () => {
    mockedGetRecipeIngredients.mockRejectedValue({
      message: 'Network error',
    });
    const { findByText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_err" />
    );
    expect(await findByText(/Could not load ingredients/i)).toBeInTheDocument();
  });
});

describe('NormalizedIngredientList — empty state', () => {
  it('shows empty state when no ingredients returned', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(makeTestResponse([]));
    const { findByText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_empty" />
    );
    expect(await findByText(/No ingredients found/i)).toBeInTheDocument();
  });
});

describe('NormalizedIngredientList — populated state', () => {
  it('renders ingredient names from API response', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([
        makeTestIngredient({ canonical_name: 'paneer', display_name: 'Paneer' }),
        makeTestIngredient({
          raw_text: '2 onions',
          display_name: 'Onions',
          canonical_name: 'onion',
          category: 'vegetable',
          quantity: 2,
          unit: null,
        }),
      ])
    );
    const { findByText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );
    expect(await findByText('Paneer')).toBeInTheDocument();
    expect(await findByText('Onion')).toBeInTheDocument();
  });

  it('renders ingredient count header', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([
        makeTestIngredient(),
        makeTestIngredient({
          canonical_name: 'onion',
          display_name: 'Onion',
          raw_text: '2 onions',
        }),
      ])
    );
    const { findByText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );
    expect(await findByText('2 items')).toBeInTheDocument();
  });

  it('shows category badge for ingredient with known category', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([makeTestIngredient({ category: 'dairy' })])
    );
    const { findByLabelText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );
    expect(await findByLabelText('Category: dairy')).toBeInTheDocument();
  });

  it('shows optional badge for optional ingredient', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([makeTestIngredient({ optional: true })])
    );
    const { findByLabelText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );
    expect(await findByLabelText('This ingredient is optional')).toBeInTheDocument();
  });

  it('shows To Taste badge for to_taste ingredient', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([
        makeTestIngredient({
          to_taste: true,
          quantity: null,
          unit: null,
          canonical_name: 'salt',
          display_name: 'Salt',
        }),
      ])
    );
    const { findByLabelText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );
    expect(
      await findByLabelText('No fixed quantity — add to taste')
    ).toBeInTheDocument();
  });

  it('shows preparation note badge', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([makeTestIngredient({ preparation_note: 'finely chopped' })])
    );
    const { findByLabelText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );
    expect(await findByLabelText('Preparation: finely chopped')).toBeInTheDocument();
  });

  it('renders unknown ingredient without crashing', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([
        makeTestIngredient({
          canonical_name: 'dragon bark xyz',
          display_name: 'Dragon Bark Xyz',
          category: null,
          matched_alias: null,
          normalization_source: 'unknown',
          confidence_score: 0.45,
        }),
      ])
    );
    const { findByText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );
    expect(await findByText('Dragon Bark Xyz')).toBeInTheDocument();
  });

  it('highlights pantry ingredient', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([makeTestIngredient({ canonical_name: 'paneer' })])
    );
    const pantrySet = new Set(['paneer']);
    const { findByText } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" pantryIngredients={pantrySet} />
    );
    expect(await findByText('In Pantry')).toBeInTheDocument();
  });

  it('11. Clicking Quick Match button opens modal, and closing modal resets state', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([makeTestIngredient({ canonical_name: 'paneer', display_name: 'Paneer' })])
    );

    const { findByTestId, queryByTestId } = renderWithQueryClient(
      <NormalizedIngredientList recipeId="recipe_123" />
    );

    // Find and click the match button
    const matchBtn = await findByTestId('quick-match-button-paneer');
    expect(matchBtn).toBeInTheDocument();

    fireEvent.click(matchBtn);

    // Modal is opened
    const modal = await findByTestId('grocery-quick-match-modal');
    expect(modal).toBeInTheDocument();
    expect(screen.getByText(/Quick Match for "paneer"/i)).toBeInTheDocument();

    // Close the modal
    const closeBtn = screen.getByTestId('quick-match-close-button');
    fireEvent.click(closeBtn);

    // Modal is closed
    expect(queryByTestId('grocery-quick-match-modal')).not.toBeInTheDocument();
  });

  it('allows selecting and deselecting ingredients', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([makeTestIngredient({ canonical_name: 'paneer', display_name: 'Paneer' })])
    );

    renderWithQueryClient(<NormalizedIngredientList recipeId="recipe_123" />);

    // Paneer should start unchecked (displays "Not in pantry" circle)
    const toggleContainer = await screen.findByTestId('ingredient-select-paneer');
    expect(screen.getByLabelText('Not in pantry')).toBeInTheDocument();

    // Click to select
    fireEvent.click(toggleContainer);
    expect(screen.getByLabelText('In pantry')).toBeInTheDocument();

    // Click to deselect
    fireEvent.click(toggleContainer);
    expect(screen.getByLabelText('Not in pantry')).toBeInTheDocument();
  });

  it('supports multiple ingredient selections concurrently', async () => {
    mockedGetRecipeIngredients.mockResolvedValue(
      makeTestResponse([
        makeTestIngredient({ canonical_name: 'paneer', display_name: 'Paneer' }),
        makeTestIngredient({ canonical_name: 'tomatoes', display_name: 'Tomatoes' }),
      ])
    );

    renderWithQueryClient(<NormalizedIngredientList recipeId="recipe_123" />);

    const paneerToggle = await screen.findByTestId('ingredient-select-paneer');
    const tomatoesToggle = screen.getByTestId('ingredient-select-tomatoes');

    // Both start unchecked
    expect(screen.getAllByLabelText('Not in pantry')).toHaveLength(2);

    // Select paneer
    fireEvent.click(paneerToggle);
    expect(screen.getByLabelText('In pantry')).toBeInTheDocument();
    expect(screen.getByLabelText('Not in pantry')).toBeInTheDocument();

    // Select tomatoes
    fireEvent.click(tomatoesToggle);
    expect(screen.getAllByLabelText('In pantry')).toHaveLength(2);
  });
});
