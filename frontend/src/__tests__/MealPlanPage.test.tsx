import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MealPlanPage } from '../pages/MealPlanPage';
import * as mealPlanApi from '../api/mealPlanApi';

// Mock meal plan API
vi.mock('../api/mealPlanApi', () => ({
  getMealPlans: vi.fn(),
  createMealPlan: vi.fn(),
  addMealToPlan: vi.fn(),
  updatePlannedMeal: vi.fn(),
  removePlannedMeal: vi.fn(),
  generateShoppingList: vi.fn(),
  getShoppingList: vi.fn(),
  getShoppingLists: vi.fn(),
  createShoppingList: vi.fn(),
  addManualShoppingItem: vi.fn(),
  updateShoppingListItem: vi.fn(),
  deleteShoppingListItem: vi.fn(),
  getShoppingListGroceryComparison: vi.fn(),
}));

const mockMealPlan = {
  id: 'plan-123',
  name: 'Diwali Week Dinners',
  start_date: '2026-11-01',
  end_date: '2026-11-07',
  created_at: '2026-10-18T12:00:00Z',
  updated_at: '2026-10-18T12:00:00Z',
  meals: [
    {
      id: 'meal-1',
      meal_plan_id: 'plan-123',
      recipe_id: 'rec-1',
      recipe_name: 'Paneer Butter Masala',
      recipe_cuisine: 'North Indian',
      meal_date: '2026-11-01',
      meal_type: 'dinner',
      servings: 4,
      original_servings: 4,
      notes: null,
      created_at: '2026-10-18T12:00:00Z',
      updated_at: '2026-10-18T12:00:00Z',
    },
  ],
};

const mockShoppingList = {
  id: 'list-123',
  meal_plan_id: 'plan-123',
  name: 'Diwali Week Dinners — Shopping List',
  status: 'active',
  total_items: 2,
  obtained_items: 0,
  created_at: '2026-10-18T12:00:00Z',
  updated_at: '2026-10-18T12:00:00Z',
  items: [
    {
      id: 'item-1',
      shopping_list_id: 'list-123',
      ingredient_name: 'paneer',
      required_quantity: 400.0,
      unit: 'g',
      pantry_quantity: 100.0,
      quantity_to_buy: 300.0,
      effective_quantity: 300.0,
      is_obtained: false,
      is_manual: false,
      source_recipes: [
        { recipe_id: 'rec-1', recipe_name: 'Paneer Butter Masala', quantity: 400.0, unit: 'g' },
      ],
      notes: 'Partially covered by pantry (100g in stock)',
      created_at: '2026-10-18T12:00:00Z',
      updated_at: '2026-10-18T12:00:00Z',
    },
    {
      id: 'item-2',
      shopping_list_id: 'list-123',
      ingredient_name: 'butter',
      required_quantity: 50.0,
      unit: 'g',
      pantry_quantity: 0.0,
      quantity_to_buy: 50.0,
      effective_quantity: 50.0,
      is_obtained: false,
      is_manual: false,
      source_recipes: [
        { recipe_id: 'rec-1', recipe_name: 'Paneer Butter Masala', quantity: 50.0, unit: 'g' },
      ],
      notes: null,
      created_at: '2026-10-18T12:00:00Z',
      updated_at: '2026-10-18T12:00:00Z',
    },
  ],
};

const renderPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <MealPlanPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('MealPlanPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(mealPlanApi.getMealPlans).mockResolvedValue([mockMealPlan]);
    vi.mocked(mealPlanApi.generateShoppingList).mockResolvedValue(mockShoppingList);
  });

  it('renders page title and meal plan name', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Meal Planning & Shopping Lists/i)).toBeInTheDocument();
      expect(screen.getAllByText('Diwali Week Dinners')[0]).toBeInTheDocument();
    });
  });

  it('renders scheduled meal cards with serving count', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Paneer Butter Masala')).toBeInTheDocument();
      expect(screen.getByText('dinner')).toBeInTheDocument();
      expect(screen.getByText('4')).toBeInTheDocument();
    });
  });

  it('switches to shopping list tab and displays consolidated items', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Paneer Butter Masala')).toBeInTheDocument();
    });

    const shoppingListTab = screen.getByRole('button', { name: /Shopping List/i });
    fireEvent.click(shoppingListTab);

    await waitFor(() => {
      expect(screen.getByText('paneer')).toBeInTheDocument();
      expect(screen.getByText('butter')).toBeInTheDocument();
      expect(screen.getByText(/300 g/i)).toBeInTheDocument();
      expect(screen.getByText(/Partially covered by pantry/i)).toBeInTheDocument();
    });
  });

  it('toggles item obtained status in shopping list', async () => {
    vi.mocked(mealPlanApi.updateShoppingListItem).mockResolvedValue({
      ...mockShoppingList.items[0],
      is_obtained: true,
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Paneer Butter Masala')).toBeInTheDocument();
    });

    const shoppingListTab = screen.getByRole('button', { name: /Shopping List/i });
    fireEvent.click(shoppingListTab);

    await waitFor(() => {
      expect(screen.getByText('paneer')).toBeInTheDocument();
    });

    const toggleButton = screen.getByTestId('toggle-obtained-item-1');
    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(mealPlanApi.updateShoppingListItem).toHaveBeenCalledWith(
        'list-123',
        'item-1',
        { is_obtained: true }
      );
    });
  });

  it('successfully adds manual item even when shopping list is initially null', async () => {
    vi.mocked(mealPlanApi.getMealPlans).mockResolvedValue([]);
    vi.mocked(mealPlanApi.getShoppingLists).mockResolvedValue([]);
    vi.mocked(mealPlanApi.createMealPlan).mockResolvedValue(mockMealPlan);
    vi.mocked(mealPlanApi.generateShoppingList).mockResolvedValue({
      ...mockShoppingList,
      items: [],
      total_items: 0,
    });
    vi.mocked(mealPlanApi.addManualShoppingItem).mockResolvedValue({
      id: 'manual-1',
      shopping_list_id: 'list-123',
      ingredient_name: 'olive',
      required_quantity: 2,
      unit: 'ltr',
      pantry_quantity: 0,
      quantity_to_buy: 2,
      effective_quantity: 2,
      is_obtained: false,
      is_manual: true,
      source_recipes: [],
      notes: null,
      created_at: '2026-10-24T12:00:00Z',
      updated_at: '2026-10-24T12:00:00Z',
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Meal Planning & Shopping Lists/i)).toBeInTheDocument();
    });

    const shoppingListTab = screen.getByRole('button', { name: /Shopping List/i });
    fireEvent.click(shoppingListTab);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Add extra item/i)).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText(/Add extra item/i);
    const qtyInput = screen.getByDisplayValue('1');
    const unitInput = screen.getByPlaceholderText(/Unit/i);
    const addButton = screen.getByRole('button', { name: /Add Item/i });

    fireEvent.change(nameInput, { target: { value: 'olive' } });
    fireEvent.change(qtyInput, { target: { value: '2' } });
    fireEvent.change(unitInput, { target: { value: 'ltr' } });

    fireEvent.click(addButton);

    await waitFor(() => {
      expect(mealPlanApi.addManualShoppingItem).toHaveBeenCalledWith('list-123', {
        ingredient_name: 'olive',
        quantity: 2,
        unit: 'ltr',
      });
      expect(screen.getByText('olive')).toBeInTheDocument();
    });
  });
});
