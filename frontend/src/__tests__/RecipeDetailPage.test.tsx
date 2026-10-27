import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RecipeDetailPage } from '../pages/RecipeDetailPage';
import * as recipesApi from '../api/recipes';
import * as ingredientsApi from '../api/ingredients';
import * as cookingHooks from '../hooks/useCooking';
import { RecipeDetail } from '../types';

vi.mock('../api/recipes', () => ({
  getRecipe: vi.fn(),
}));

vi.mock('../api/ingredients', () => ({
  getRecipeIngredients: vi.fn(),
}));

vi.mock('../hooks/useCooking', () => ({
  useStartCooking: vi.fn(),
  useActiveCookingSession: vi.fn().mockReturnValue({ data: null, isLoading: false }),
}));

vi.mock('../hooks/usePantry', () => ({
  usePantryItems: vi.fn().mockReturnValue({ data: [] }),
}));

import * as pantryHooks from '../hooks/usePantry';

const mockRecipe: RecipeDetail = {
  id: 'recipe-test-1',
  name: 'Authentic Paneer Butter Masala',
  description: 'A rich and creamy curry made with paneer, butter, and spiced tomato sauce.',
  cuisine: 'North Indian',
  dietary_type: 'Vegetarian',
  preparation_minutes: 15,
  cooking_minutes: 25,
  servings: 4,
  source_name: "Archana's Kitchen",
  average_rating: 4.8,
  created_at: '2026-01-01T00:00:00Z',
  source_url: 'https://archanaskitchen.com/paneer-butter-masala',
  author: 'Chef Sanjeev',
  source_license: 'CC-BY-SA 4.0',
  region: 'North India',
  state: 'Punjab',
  original_name: 'Paneer Makhani',
  is_indian_recipe: true,
  verification_status: 'VERIFIED',
  instructions: [
    'Cut paneer into cubes and set aside.',
    'Heat butter in a pan and saute onions and ginger-garlic paste.',
    'Add tomato puree and cook until oil separates.',
    'Add cream, garam masala, and paneer cubes, and simmer for 5 minutes.',
  ],
  structured_instructions: [
    {
      step_number: 1,
      text: 'Cut paneer into cubes and set aside.',
      action_type: 'PREP',
      timing_minutes: 5,
      temperature: null,
      equipment: ['knife', 'chopping board'],
      ingredients: ['paneer'],
    },
    {
      step_number: 2,
      text: 'Heat butter in a pan and saute onions and ginger-garlic paste.',
      action_type: 'SAUTE',
      timing_minutes: 5,
      temperature: 'Medium heat',
      equipment: ['pan', 'spatula'],
      ingredients: ['butter', 'onions', 'ginger-garlic paste'],
    },
  ],
  ingredients: [
    {
      id: 'ri-1',
      ingredient: {
        id: 'ing-1',
        canonical_name: 'paneer',
        category: 'Dairy',
        default_unit: 'grams',
      },
      raw_text: '200g fresh paneer',
      quantity: 200,
      unit: 'g',
      preparation_note: 'cubed',
    },
  ],
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('RecipeDetailPage Component', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();

    (cookingHooks.useStartCooking as any).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    (ingredientsApi.getRecipeIngredients as any).mockResolvedValue({
      results: [
        {
          canonical_name: 'paneer',
          display_name: 'fresh paneer',
          quantity: 200,
          unit: 'g',
          preparation_note: 'cubed',
          optional: false,
          to_taste: false,
          category: 'Dairy',
          confidence_score: 0.95,
          matched_alias: 'paneer',
          normalization_source: 'curated',
          parser_version: '2.0',
        },
      ],
      total: 1,
    });
  });

  const renderComponent = (recipeId = 'recipe-test-1') => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/recipes/${recipeId}`]}>
          <Routes>
            <Route path="/recipes/:id" element={<RecipeDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('renders loading state initially when fetching recipe', () => {
    (recipesApi.getRecipe as any).mockReturnValue(new Promise(() => {}));
    renderComponent();
    expect(screen.getByText(/Loading recipe details.../i)).toBeInTheDocument();
  });

  it('renders error state when fetch fails', async () => {
    (recipesApi.getRecipe as any).mockRejectedValue(new Error('Network connection failed'));
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Could not load recipe/i)).toBeInTheDocument();
      expect(screen.getByText(/Network connection failed/i)).toBeInTheDocument();
    });
  });

  it('renders recipe title, tags, description, prep/cook times, and default servings', async () => {
    (recipesApi.getRecipe as any).mockResolvedValue(mockRecipe);
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Authentic Paneer Butter Masala')).toBeInTheDocument();
    });

    expect(screen.getByText(/North Indian Cuisine/i)).toBeInTheDocument();
    expect(screen.getByText(/Vegetarian/i)).toBeInTheDocument();
    expect(screen.getByText(/Prep: 15 mins • Cook: 25 mins/i)).toBeInTheDocument();
    expect(screen.getByTestId('serving-count')).toHaveTextContent('4');
  });

  it('adjusts servings up and down and updates Compare Prices link', async () => {
    (recipesApi.getRecipe as any).mockResolvedValue(mockRecipe);
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('serving-count')).toHaveTextContent('4');
    });

    // Check initial Compare Prices href
    const compareLink = screen.getByRole('link', { name: /Compare Prices/i });
    expect(compareLink).toHaveAttribute('href', '/grocery?recipeId=recipe-test-1&servings=4&baseServings=4');

    // Increase servings to 5
    const increaseBtn = screen.getByTestId('increase-servings');
    fireEvent.click(increaseBtn);

    expect(screen.getByTestId('serving-count')).toHaveTextContent('5');
    expect(compareLink).toHaveAttribute('href', '/grocery?recipeId=recipe-test-1&servings=5&baseServings=4');

    // Reset button should now be visible
    const resetBtn = screen.getByTestId('reset-servings');
    expect(resetBtn).toBeInTheDocument();
    fireEvent.click(resetBtn);

    // Servings reset back to 4
    expect(screen.getByTestId('serving-count')).toHaveTextContent('4');
    expect(screen.queryByTestId('reset-servings')).not.toBeInTheDocument();
  });

  it('respects minimum serving limit of 1', async () => {
    (recipesApi.getRecipe as any).mockResolvedValue({ ...mockRecipe, servings: 1 });
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('serving-count')).toHaveTextContent('1');
    });

    const decreaseBtn = screen.getByTestId('decrease-servings');
    expect(decreaseBtn).toBeDisabled();
  });

  it('renders provenance and attribution details', async () => {
    (recipesApi.getRecipe as any).mockResolvedValue(mockRecipe);
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('recipe-provenance')).toBeInTheDocument();
    });

    expect(screen.getByText("Archana's Kitchen")).toBeInTheDocument();
    expect(screen.getByText('Chef Sanjeev')).toBeInTheDocument();
    expect(screen.getByText('Punjab')).toBeInTheDocument();
    expect(screen.getByText('CC-BY-SA 4.0')).toBeInTheDocument();
    expect(screen.getByText(/View Original Recipe/i)).toBeInTheDocument();
  });

  it('renders structured instructions when available', async () => {
    (recipesApi.getRecipe as any).mockResolvedValue(mockRecipe);
    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('structured-instructions')).toBeInTheDocument();
    });

    expect(screen.getByText('PREP')).toBeInTheDocument();
    expect(screen.getByText('SAUTE')).toBeInTheDocument();
    expect(screen.getByText('Medium heat')).toBeInTheDocument();
  });

  it('marks recipe ingredients present in user pantry as In Pantry and done', async () => {
    (recipesApi.getRecipe as any).mockResolvedValue(mockRecipe);
    (pantryHooks.usePantryItems as any).mockReturnValue({
      data: [
        {
          id: 'p-1',
          ingredient_id: 'ing-1',
          canonical_name: 'paneer',
          ingredient_name: 'Paneer',
          quantity: 200,
          unit: 'g',
          expiration_date: null,
        },
      ],
      isLoading: false,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Authentic Paneer Butter Masala')).toBeInTheDocument();
    });

    // Check that Paneer row displays "In Pantry" badge and is marked done
    expect(await screen.findByText('In Pantry')).toBeInTheDocument();
    expect(screen.getByTestId('pantry-count-indicator')).toHaveTextContent('• 1 in pantry');
    expect(screen.getByLabelText('In pantry')).toBeInTheDocument();
  });
});
