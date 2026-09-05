import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { CartOptimizationPanel } from '../components/grocery/CartOptimizationPanel';
import * as cartHooks from '../hooks/useCartOptimization';
import * as ingredientsApi from '../api/ingredients';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock the modules
vi.mock('../hooks/useCartOptimization', () => ({
  useCartOptimize: vi.fn(),
}));

vi.mock('../api/ingredients', () => ({
  getRecipeIngredients: vi.fn(),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('CartOptimizationPanel Component', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
    
    // Default mocked implementation of useCartOptimize to prevent TypeError destructuring on mount
    (cartHooks.useCartOptimize as any).mockReturnValue({
      mutate: vi.fn(),
      data: null,
      isPending: false,
      isError: false,
      error: null,
    });
  });

  const renderComponent = (search = '?recipeId=recipe-123') => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/grocery${search}`]}>
          <CartOptimizationPanel />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('1. Renders prompt to select recipe when recipeId is missing', () => {
    renderComponent('');
    expect(screen.getByText(/No Recipe Selected for Optimization/i)).toBeInTheDocument();
  });

  it('2. Shows loading state while loading recipe ingredients', () => {
    vi.spyOn(ingredientsApi, 'getRecipeIngredients').mockReturnValue(
      new Promise(() => {}) // never resolves to stay in loading state
    );

    renderComponent();
    expect(screen.getByTestId('cart-optimize-loading')).toBeInTheDocument();
  });

  it('3. Renders error state if loading ingredients fails', async () => {
    vi.spyOn(ingredientsApi, 'getRecipeIngredients').mockRejectedValue(
      new Error('Ingredients API down')
    );

    renderComponent();
    
    const errorElem = await screen.findByTestId('cart-optimize-error');
    expect(errorElem).toBeInTheDocument();
    expect(screen.getByText('Ingredients API down')).toBeInTheDocument();
  });

  it('4. Renders optimization pending/spinner state when calculation is running', async () => {
    vi.spyOn(ingredientsApi, 'getRecipeIngredients').mockResolvedValue({
      count: 1,
      results: [
        {
          raw_text: 'Paneer 500g',
          display_name: 'Paneer',
          canonical_name: 'paneer',
          category: 'dairy',
          quantity: 500,
          unit: 'g',
          preparation_note: null,
          optional: false,
          to_taste: false,
          confidence_score: 1.0,
          matched_alias: 'paneer',
          normalization_source: 'dictionary',
          parser_version: '1.0',
        },
      ],
    });

    (cartHooks.useCartOptimize as any).mockReturnValue({
      mutate: vi.fn(),
      data: null,
      isPending: true,
      isError: false,
      error: null,
    });

    renderComponent();

    // The component should render the optimization header and the loader
    expect(await screen.findByTestId('cart-optimize-pending')).toBeInTheDocument();
  });

  it('5. Renders optimization results, totals, savings, freshness, and demo disclaimer', async () => {
    vi.spyOn(ingredientsApi, 'getRecipeIngredients').mockResolvedValue({
      count: 1,
      results: [
        {
          raw_text: 'Paneer 500g',
          display_name: 'Paneer',
          canonical_name: 'paneer',
          category: 'dairy',
          quantity: 500,
          unit: 'g',
          preparation_note: null,
          optional: false,
          to_taste: false,
          confidence_score: 1.0,
          matched_alias: 'paneer',
          normalization_source: 'dictionary',
          parser_version: '1.0',
        },
      ],
    });

    const mockResponse = {
      recommended_strategy: 'cheapest_split_cart',
      total_cost: 325.0,
      currency: 'INR',
      estimated_savings: 45.0,
      stores_used: 2,
      price_freshness: 'CACHED',
      data_source: 'demo',
      explanation: 'Split cart across Demo QuickMart and Demo FreshBasket saves ₹45.',
      recommended_cart: {
        strategy: 'cheapest_split_cart',
        stores_used: 2,
        total_cost: 325.0,
        currency: 'INR',
        missing_ingredients: [],
        explanation: 'Split cart across 2 stores.',
        stores: [
          {
            store_id: 's1',
            store_name: 'Demo QuickMart',
            subtotal: 180.0,
            delivery_fee: 30.0,
            total: 210.0,
            complete: true,
            selected_products: [
              {
                ingredient_name: 'paneer',
                product_id: 'p1',
                product_name: 'Paneer 500g',
                brand: 'Amul',
                package_quantity: 500.0,
                package_unit: 'g',
                packages_required: 1,
                package_price: 180.0,
                line_cost: 180.0,
                currency: 'INR',
                match_score: 0.95,
                in_stock: true,
                data_source_type: 'demo',
                price_freshness: 'CACHED',
              },
            ],
            missing_ingredients: [],
          },
        ],
      },
      alternatives: [],
      missing_ingredients: [],
    };

    const optimizeMock = vi.fn();
    (cartHooks.useCartOptimize as any).mockReturnValue({
      mutate: optimizeMock,
      data: mockResponse,
      isPending: false,
      isError: false,
      error: null,
    });

    renderComponent();

    // Verify optimization result components render
    expect(await screen.findByTestId('optimization-results')).toBeInTheDocument();
    expect(screen.getByText(/Cheapest Split Cart/i)).toBeInTheDocument();
    expect(screen.getByTestId('recommended-total')).toHaveTextContent(/₹325/);
    expect(screen.getByTestId('estimated-savings')).toHaveTextContent(/save ₹45/i);
    expect(screen.getByTestId('store-name')).toHaveTextContent('Demo QuickMart');
    expect(screen.getByTestId('product-name')).toHaveTextContent('Paneer 500g');
    expect(screen.getByText(/Demonstration Notice:/i)).toBeInTheDocument();
  });

  it('6. Displays missing/unfulfilled ingredients if reported', async () => {
    // Return at least one ingredient to bypass the "no ingredients to optimize" early return
    vi.spyOn(ingredientsApi, 'getRecipeIngredients').mockResolvedValue({
      count: 2,
      results: [
        {
          raw_text: 'Fresh Curry Leaves',
          display_name: 'Curry Leaves',
          canonical_name: 'fresh curry leaves',
          category: 'herb',
          quantity: 1,
          unit: 'piece',
          preparation_note: null,
          optional: false,
          to_taste: false,
          confidence_score: 1.0,
          matched_alias: 'curry leaves',
          normalization_source: 'dictionary',
          parser_version: '1.0',
        },
      ],
    });

    const mockResponse = {
      recommended_strategy: 'none_available',
      total_cost: 0.0,
      currency: 'INR',
      estimated_savings: 0.0,
      stores_used: 0,
      price_freshness: 'CACHED',
      data_source: 'demo',
      explanation: 'No complete shopping plan could be constructed.',
      recommended_cart: {
        strategy: 'none_available',
        stores_used: 0,
        total_cost: 0.0,
        currency: 'INR',
        missing_ingredients: [
          { ingredient_name: 'fresh curry leaves', reason: 'No compatible in-stock product found' },
        ],
        stores: [],
      },
      alternatives: [],
      missing_ingredients: [
        { ingredient_name: 'fresh curry leaves', reason: 'No compatible in-stock product found' },
      ],
    };

    (cartHooks.useCartOptimize as any).mockReturnValue({
      mutate: vi.fn(),
      data: mockResponse,
      isPending: false,
      isError: false,
      error: null,
    });

    renderComponent();

    expect(await screen.findByTestId('missing-ingredients')).toBeInTheDocument();
    expect(screen.getByText('fresh curry leaves')).toBeInTheDocument();
    expect(screen.getByText('No compatible in-stock product found')).toBeInTheDocument();
  });
});
