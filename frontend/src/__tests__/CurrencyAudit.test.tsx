import { render, screen } from '@testing-library/react';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfilePage } from '../pages/ProfilePage';
import { PantryPage } from '../pages/PantryPage';
import { RecipeDetailPage } from '../pages/RecipeDetailPage';
import { PriceComparisonCard } from '../components/grocery/PriceComparisonCard';
import { formatINR, formatPrice } from '../utils/currency';

vi.mock('../api/recipes', () => ({
  getRecipe: vi.fn().mockResolvedValue({
    id: '1',
    name: 'Paneer Bhurji',
    cuisine: 'Indian',
    average_rating: 4.8,
    servings: 4,
    preparation_minutes: 10,
    cooking_minutes: 15,
    description: 'Scrambled paneer',
    instructions: ['Step 1'],
    ingredients: [],
  }),
}));

vi.mock('../api/profile', () => ({
  getProfile: vi.fn().mockResolvedValue({
    id: 'user-123',
    email: 'rajesh@example.com',
    full_name: 'Rajesh Kumar',
    preference: {
      dietary_type: 'Vegetarian',
      weekly_budget: 2500,
      household_size: 4,
      disliked_ingredients: [],
    },
  }),
  updateProfile: vi.fn(),
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const mockStore = {
  id: 'store_1',
  name: 'Demo QuickMart',
  store_type: 'Convenience Supermarket',
  city: 'Demo City',
  is_demo_store: true,
  created_at: '2026-08-04T00:00:00Z',
};

describe('Global INR Currency Audit', () => {
  it('ProfilePage renders INR symbol ₹ and no $ dollar sign', async () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ProfilePage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Wait for the profile data to load and render the target values
    expect(await screen.findByText('Rajesh Kumar')).toBeInTheDocument();

    // Assert ₹ symbol is present in text
    expect(screen.getAllByText(/₹/).length).toBeGreaterThan(0);
    // Assert no $ symbol appears in rendered container HTML
    expect(container.innerHTML).not.toContain('$');
  });

  it('PantryPage renders no $ dollar sign (live API, no hardcoded currency)', () => {
    // PantryPage now fetches live data — mock the API so it doesn't hang
    vi.mock('../api/pantry', () => ({
      getPantryItems: vi.fn().mockResolvedValue([]),
      addPantryItem: vi.fn(),
      updatePantryItem: vi.fn(),
      deletePantryItem: vi.fn(),
    }));
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <PantryPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // PantryPage must never render a $ symbol
    expect(container.innerHTML).not.toContain('$');
  });

  it('RecipeDetailPage renders INR symbol ₹ and no $ dollar sign', async () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/recipes/1']}>
          <Routes>
            <Route path="/recipes/:id" element={<RecipeDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Paneer Bhurji')).toBeInTheDocument();
    expect(screen.getAllByText(/₹/).length).toBeGreaterThan(0);
    expect(container.innerHTML).not.toContain('$');
  });

  it('PriceComparisonCard renders INR symbol ₹ and no $ dollar sign', () => {
    const { container } = render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={0} />
    );

    const rupeeElements = screen.getAllByText('₹95');
    expect(rupeeElements.length).toBeGreaterThanOrEqual(1);
    expect(container.innerHTML).not.toContain('$');
  });

  it('currency field defaults and enforces "INR"', () => {
    expect(formatPrice(95, 'INR')).toBe('₹95');
    expect(formatINR(1250)).toBe('₹1,250');
    expect(formatINR(5499)).toBe('₹5,499');
  });
});
