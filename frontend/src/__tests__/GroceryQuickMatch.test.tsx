import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroceryQuickMatch } from '../components/grocery/GroceryQuickMatch';
import { ProductMatchResult, BestProductOption } from '../types';
import * as useGroceryHooks from '../hooks/useGrocery';

const sampleResult: ProductMatchResult = {
  product_id: 'p1',
  product_name: 'Amul Fresh Paneer 200g',
  brand: 'Amul',
  category: 'Dairy',
  store_id: 's1',
  store_name: 'Demo QuickMart',
  price: 95.0,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.475,
  base_unit: 'g',
  similarity_score: 0.92,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 1,
  price_rank: 1,
};

const sampleBestOption: BestProductOption = {
  product_id: 'p1',
  product_name: 'Amul Fresh Paneer 200g',
  store_id: 's1',
  store_name: 'Demo QuickMart',
  brand: 'Amul',
  category: 'Dairy',
  price: 95.0,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.475,
  base_unit: 'g',
  similarity_score: 0.92,
};

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('GroceryQuickMatch Modal Component', () => {
  it('1. Quick Match is closed by default when isOpen=false', () => {
    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByTestId('grocery-quick-match-modal')).not.toBeInTheDocument();
  });

  it('2. Quick Match opens when isOpen=true and displays selected ingredient name', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByTestId('grocery-quick-match-modal')).toBeInTheDocument();
    expect(screen.getByText(/Quick Match for "paneer"/i)).toBeInTheDocument();
  });

  it('3. Renders product name, store name, INR package price, unit price, similarity %, and Best Value badge', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText('Amul Fresh Paneer 200g')).toBeInTheDocument();
    expect(screen.getByText('Demo QuickMart')).toBeInTheDocument();
    expect(screen.getByText(/₹95/)).toBeInTheDocument();
    expect(screen.getByText(/₹0.48\/g|₹0.475\/g|₹0.475/)).toBeInTheDocument();
    expect(screen.getByText('92% match')).toBeInTheDocument();
    expect(screen.getByTestId('best-value-badge')).toBeInTheDocument();
  });

  it('4. Handles best_option === null safely without crash or false Best Value badge', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult],
        best_option: null,
        comparison_mode: null,
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByText('Amul Fresh Paneer 200g')).toBeInTheDocument();
    expect(screen.queryByTestId('best-value-badge')).not.toBeInTheDocument();
  });

  it('5. Renders loading state placeholders when fetching matches', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByTestId('quick-match-loading')).toBeInTheDocument();
  });

  it('6. Renders empty state card when total_matches === 0', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'dragonfruitxyz',
        canonical_name: 'dragonfruitxyz',
        threshold: 0.4,
        total_matches: 0,
        results: [],
        best_option: null,
        comparison_mode: null,
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="dragonfruitxyz" isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByTestId('quick-match-empty')).toBeInTheDocument();
    expect(screen.getByText('No matching grocery products found.')).toBeInTheDocument();
  });

  it('7. Renders error state card with retry action button', () => {
    const refetchMock = vi.fn();
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: { message: 'Grocery service temporarily offline' },
      refetch: refetchMock,
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByTestId('quick-match-error')).toBeInTheDocument();
    expect(screen.getByText('Grocery service temporarily offline')).toBeInTheDocument();

    const retryBtn = screen.getByRole('button', { name: /retry/i });
    fireEvent.click(retryBtn);
    expect(refetchMock).toHaveBeenCalledTimes(1);
  });

  it('8. Clicking close button triggers onClose callback', () => {
    const onCloseMock = vi.fn();
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={true} onClose={onCloseMock} />);
    const closeBtn = screen.getByTestId('quick-match-close-button');
    fireEvent.click(closeBtn);
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('9. Dialog has accessible role, aria-modal="true", and aria-labelledby', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={true} onClose={vi.fn()} />);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'quick-match-dialog-title');
  });

  it('10. Pressing Escape key triggers onClose callback', () => {
    const onCloseMock = vi.fn();
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    renderWithQueryClient(<GroceryQuickMatch ingredient="paneer" isOpen={true} onClose={onCloseMock} />);

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });
});
