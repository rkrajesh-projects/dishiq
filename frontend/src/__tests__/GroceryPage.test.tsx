import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroceryPage } from '../pages/GroceryPage';
import * as groceryApi from '../api/grocery';

// Mock API modules
vi.mock('../api/grocery', () => ({
  getStores: vi.fn(),
  getProducts: vi.fn(),
}));

// Lightweight mocks for heavy child components
vi.mock('../components/grocery/CartOptimizationPanel', () => ({
  CartOptimizationPanel: () => <div data-testid="mock-cart-panel" />,
}));
vi.mock('../components/grocery/GroceryPriceComparison', () => ({
  GroceryPriceComparison: () => <div data-testid="mock-price-comparison" />,
}));
vi.mock('../components/grocery/GroceryMatchList', () => ({
  GroceryMatchList: () => <div data-testid="mock-match-list" />,
}));

// Two stores: store 1 is cheapest (₹412), store 2 is more expensive (₹503.8)
const mockStores = {
  items: [
    {
      id: '1',
      name: 'Demo QuickMart',
      store_type: 'Convenience Supermarket',
      city: 'Demo City',
      is_demo_store: true,
      created_at: '2026-08-04T00:00:00Z',
    },
    {
      id: '2',
      name: 'Demo FreshBasket',
      store_type: 'Organic Fresh Market',
      city: 'Demo City',
      is_demo_store: true,
      created_at: '2026-08-04T00:00:00Z',
    },
  ],
};

const mockProducts = {
  items: [
    {
      id: 'p1',
      name: 'Paneer 500g',
      store_id: '1',
      prices: [{ price: 412, delivery_fee: 0, in_stock: true, updated_at: '2026-08-04T00:00:00Z' }],
    },
    {
      id: 'p2',
      name: 'Organic Paneer',
      store_id: '2',
      prices: [{ price: 473.8, delivery_fee: 30, in_stock: true, updated_at: '2026-08-04T00:00:00Z' }],
    },
  ],
};

function renderGroceryPage(search = '') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/grocery${search}`]}>
        <GroceryPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('GroceryPage — Store Cart Selection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(groceryApi, 'getStores').mockResolvedValue(mockStores as any);
    vi.spyOn(groceryApi, 'getProducts').mockResolvedValue(mockProducts as any);
  });

  it('selects the cheapest store by default', async () => {
    renderGroceryPage();

    // Wait for data to load — store cards appear
    const card1 = await screen.findByTestId('store-card-1');
    const card2 = screen.getByTestId('store-card-2');

    // Store 1 (QuickMart) total = ₹412 is cheapest — selected by default (synchronously derived)
    expect(card1).toHaveClass('border-emerald-500');
    expect(card2).not.toHaveClass('border-emerald-500');
  });

  it('moves selection when clicking another store card', async () => {
    renderGroceryPage();

    const card1 = await screen.findByTestId('store-card-1');
    const card2 = screen.getByTestId('store-card-2');

    // Initially cheapest (card1) is selected
    expect(card1).toHaveClass('border-emerald-500');

    // Click card2
    fireEvent.click(card2);

    // card2 is now selected, card1 is not
    expect(card2).toHaveClass('border-emerald-500');
    expect(card1).not.toHaveClass('border-emerald-500');
  });

  it('allows re-selecting the first store after switching', async () => {
    renderGroceryPage();

    const card1 = await screen.findByTestId('store-card-1');
    const card2 = screen.getByTestId('store-card-2');

    // Switch to card2
    fireEvent.click(card2);
    expect(card2).toHaveClass('border-emerald-500');

    // Switch back to card1
    fireEvent.click(card1);
    expect(card1).toHaveClass('border-emerald-500');
    expect(card2).not.toHaveClass('border-emerald-500');
  });

  it('Best Cart badge stays on cheapest store regardless of which store is selected', async () => {
    renderGroceryPage();

    const card1 = await screen.findByTestId('store-card-1');
    const card2 = screen.getByTestId('store-card-2');

    // Best Cart badge on card1 (cheapest) before any click
    expect(card1).toContainElement(screen.getByText('Best Cart'));

    // Click card2 — selection moves, but Best Cart badge stays on card1
    fireEvent.click(card2);
    expect(card1).toContainElement(screen.getByText('Best Cart'));
    expect(card2).not.toContainElement(screen.queryByText('Best Cart')!);
  });
});
