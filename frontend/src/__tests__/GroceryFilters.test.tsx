import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { GroceryMatchList } from '../components/grocery/GroceryMatchList';
import { GroceryPriceComparison } from '../components/grocery/GroceryPriceComparison';
import { ProductMatchResult, BestProductOption } from '../types';
import * as useGroceryHooks from '../hooks/useGrocery';

const productQuickMartLow: ProductMatchResult = {
  product_id: 'p1',
  product_name: 'QuickMart Cheap Paneer 200g',
  brand: 'BrandA',
  category: 'Dairy',
  store_id: 's1',
  store_name: 'Demo QuickMart',
  price: 90.0,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.45,
  base_unit: 'g',
  similarity_score: 0.95,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 1,
  price_rank: 1,
};

const productQuickMartHigh: ProductMatchResult = {
  product_id: 'p2',
  product_name: 'QuickMart Expensive Paneer 200g',
  brand: 'BrandA',
  category: 'Dairy',
  store_id: 's1',
  store_name: 'Demo QuickMart',
  price: 130.0,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.65,
  base_unit: 'g',
  similarity_score: 0.80,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 3,
  price_rank: 3,
};

const productFreshBasketMid: ProductMatchResult = {
  product_id: 'p3',
  product_name: 'FreshBasket Organic Paneer 200g',
  brand: 'OrganicCo',
  category: 'Dairy',
  store_id: 's2',
  store_name: 'Demo FreshBasket',
  price: 110.0,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.55,
  base_unit: 'g',
  similarity_score: 0.90,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 2,
  price_rank: 2,
};

const productNoPrice: ProductMatchResult = {
  product_id: 'p4',
  product_name: 'No Price Paneer 200g',
  brand: 'Mystery',
  category: 'Dairy',
  store_id: 's3',
  store_name: 'Demo LocalGrocer',
  price: null,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: null,
  base_unit: 'g',
  similarity_score: 0.70,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 4,
  price_rank: null,
};

const bestOption: BestProductOption = {
  product_id: 'p1',
  product_name: 'QuickMart Cheap Paneer 200g',
  store_id: 's1',
  store_name: 'Demo QuickMart',
  brand: 'BrandA',
  category: 'Dairy',
  price: 90.0,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.45,
  base_unit: 'g',
  similarity_score: 0.95,
};

describe('Phase 6.4.5 — Store Filters & Sorting UI', () => {
  it('1. "All Stores" is default, dynamic store options generated, selecting store filters results', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 3,
        results: [productQuickMartLow, productFreshBasketMid, productQuickMartHigh],
        best_option: bestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);

    // Filter Bar exists
    expect(screen.getByTestId('grocery-filter-bar')).toBeInTheDocument();
    expect(screen.getByTestId('grocery-result-count')).toHaveTextContent('Showing 3 of 3 products');

    const storeSelect = screen.getByLabelText('Filter by store') as HTMLSelectElement;
    expect(storeSelect.value).toBe('all');

    // Store options: All Stores, Demo FreshBasket, Demo QuickMart
    const options = Array.from(storeSelect.options).map((o) => o.value);
    expect(options).toEqual(['all', 'Demo FreshBasket', 'Demo QuickMart']);

    // Select "Demo FreshBasket"
    fireEvent.change(storeSelect, { target: { value: 'Demo FreshBasket' } });
    expect(screen.getByTestId('grocery-result-count')).toHaveTextContent('Showing 1 of 3 products');
    expect(screen.getByText('FreshBasket Organic Paneer 200g')).toBeInTheDocument();
    expect(screen.queryByText('QuickMart Cheap Paneer 200g')).not.toBeInTheDocument();

    // Select "All Stores" again
    fireEvent.change(storeSelect, { target: { value: 'all' } });
    expect(screen.getByTestId('grocery-result-count')).toHaveTextContent('Showing 3 of 3 products');
    expect(screen.getByText('QuickMart Cheap Paneer 200g')).toBeInTheDocument();
  });

  it('2. Sorting by Price Low to High, High to Low, and Default Order', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 3,
        results: [productQuickMartHigh, productQuickMartLow, productFreshBasketMid],
        best_option: bestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);

    const sortSelect = screen.getByLabelText('Sort products') as HTMLSelectElement;

    // Price Low to High
    fireEvent.change(sortSelect, { target: { value: 'price_asc' } });
    let cards = screen.getAllByTestId(/grocery-match-card-p/);
    expect(cards[0]).toHaveAttribute('data-testid', 'grocery-match-card-p1'); // 90
    expect(cards[1]).toHaveAttribute('data-testid', 'grocery-match-card-p3'); // 110
    expect(cards[2]).toHaveAttribute('data-testid', 'grocery-match-card-p2'); // 130

    // Price High to Low
    fireEvent.change(sortSelect, { target: { value: 'price_desc' } });
    cards = screen.getAllByTestId(/grocery-match-card-p/);
    expect(cards[0]).toHaveAttribute('data-testid', 'grocery-match-card-p2'); // 130
    expect(cards[1]).toHaveAttribute('data-testid', 'grocery-match-card-p3'); // 110
    expect(cards[2]).toHaveAttribute('data-testid', 'grocery-match-card-p1'); // 90

    // Default Order (preserves original API result order: p2, p1, p3)
    fireEvent.change(sortSelect, { target: { value: 'default' } });
    cards = screen.getAllByTestId(/grocery-match-card-p/);
    expect(cards[0]).toHaveAttribute('data-testid', 'grocery-match-card-p2');
    expect(cards[1]).toHaveAttribute('data-testid', 'grocery-match-card-p1');
    expect(cards[2]).toHaveAttribute('data-testid', 'grocery-match-card-p3');
  });

  it('3. Sorting by Similarity High to Low and Low to High', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 3,
        results: [productQuickMartHigh, productQuickMartLow, productFreshBasketMid],
        best_option: bestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);
    const sortSelect = screen.getByLabelText('Sort products') as HTMLSelectElement;

    // Similarity High to Low (p1: 0.95, p3: 0.90, p2: 0.80)
    fireEvent.change(sortSelect, { target: { value: 'similarity_desc' } });
    let cards = screen.getAllByTestId(/grocery-match-card-p/);
    expect(cards[0]).toHaveAttribute('data-testid', 'grocery-match-card-p1');
    expect(cards[1]).toHaveAttribute('data-testid', 'grocery-match-card-p3');
    expect(cards[2]).toHaveAttribute('data-testid', 'grocery-match-card-p2');

    // Similarity Low to High (p2: 0.80, p3: 0.90, p1: 0.95)
    fireEvent.change(sortSelect, { target: { value: 'similarity_asc' } });
    cards = screen.getAllByTestId(/grocery-match-card-p/);
    expect(cards[0]).toHaveAttribute('data-testid', 'grocery-match-card-p2');
    expect(cards[1]).toHaveAttribute('data-testid', 'grocery-match-card-p3');
    expect(cards[2]).toHaveAttribute('data-testid', 'grocery-match-card-p1');
  });

  it('4. Handles null prices safely (places products with null price at the bottom)', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 3,
        results: [productNoPrice, productQuickMartHigh, productQuickMartLow],
        best_option: bestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);
    const sortSelect = screen.getByLabelText('Sort products') as HTMLSelectElement;

    // Price Low to High: p1 (90), p2 (130), p4 (null)
    fireEvent.change(sortSelect, { target: { value: 'price_asc' } });
    const cards = screen.getAllByTestId(/grocery-match-card-p/);
    expect(cards[0]).toHaveAttribute('data-testid', 'grocery-match-card-p1');
    expect(cards[1]).toHaveAttribute('data-testid', 'grocery-match-card-p2');
    expect(cards[2]).toHaveAttribute('data-testid', 'grocery-match-card-p4');
  });

  it('5. Filter empty state renders when selected store produces 0 results, reset button clears filter', () => {
    const mockHook = vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [productFreshBasketMid, productQuickMartLow],
        best_option: null,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    const { rerender } = render(<GroceryMatchList ingredient="paneer" />);

    const storeSelect = screen.getByLabelText('Filter by store') as HTMLSelectElement;
    fireEvent.change(storeSelect, { target: { value: 'Demo QuickMart' } });
    expect(screen.getByText('QuickMart Cheap Paneer 200g')).toBeInTheDocument();
    expect(screen.queryByText('FreshBasket Organic Paneer 200g')).not.toBeInTheDocument();

    // Now mock data update where QuickMart products are no longer in results
    mockHook.mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [productFreshBasketMid],
        best_option: null,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    rerender(<GroceryMatchList ingredient="paneer" />);

    // Since selectedStore was 'Demo QuickMart' and results now only has 'Demo FreshBasket', filteredCount is 0!
    expect(screen.getByTestId('grocery-filter-empty')).toBeInTheDocument();
    expect(screen.getByText(/No products found for "Demo QuickMart"/)).toBeInTheDocument();

    // Click "Show All Stores" button
    const showAllBtn = screen.getByRole('button', { name: /show all stores/i });
    fireEvent.click(showAllBtn);

    // Filter is reset to 'all', showing FreshBasket item!
    expect(screen.getByText('FreshBasket Organic Paneer 200g')).toBeInTheDocument();
  });

  it('6. Best Value badge remains tied to backend best_option.product_id after sorting or filtering', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [productQuickMartHigh, productQuickMartLow],
        best_option: bestOption, // p1 is best_option
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);

    const sortSelect = screen.getByLabelText('Sort products') as HTMLSelectElement;
    // Sort High to Low (p2 appears first, p1 appears second)
    fireEvent.change(sortSelect, { target: { value: 'price_desc' } });

    const cardP1 = screen.getByTestId('grocery-match-card-p1');
    const cardP2 = screen.getByTestId('grocery-match-card-p2');

    // p1 still has Best Value badge
    expect(cardP1).toHaveTextContent('Best Value');
    // p2 does NOT receive Best Value badge
    expect(cardP2).not.toHaveTextContent('Best Value');
  });

  it('7. GroceryPriceComparison respects store filter and sorting', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [productQuickMartLow, productFreshBasketMid],
        best_option: bestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);

    expect(screen.getByTestId('grocery-filter-bar')).toBeInTheDocument();
    const storeSelect = screen.getByLabelText('Filter by store') as HTMLSelectElement;

    fireEvent.change(storeSelect, { target: { value: 'Demo QuickMart' } });
    expect(screen.getByTestId('grocery-compare-item-p1')).toBeInTheDocument();
    expect(screen.queryByTestId('grocery-compare-item-p3')).not.toBeInTheDocument();
  });

  it('8. GroceryFilterBar has accessible labels on select controls', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [productQuickMartLow],
        best_option: null,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);

    // Located using accessible queries
    const storeLabel = screen.getByLabelText('Filter by store');
    const sortLabel = screen.getByLabelText('Sort products');
    expect(storeLabel).toBeInTheDocument();
    expect(sortLabel).toBeInTheDocument();
  });

  it('9. GroceryMatchList does not render filter controls when API returns 0 matches', () => {
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

    render(<GroceryMatchList ingredient="dragonfruitxyz" />);

    // Filter bar should not be present
    expect(screen.queryByTestId('grocery-filter-bar')).not.toBeInTheDocument();
  });
});
