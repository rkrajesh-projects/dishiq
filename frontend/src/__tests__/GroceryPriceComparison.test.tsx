import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { GroceryPriceComparison } from '../components/grocery/GroceryPriceComparison';
import { ProductMatchResult, BestProductOption } from '../types';
import * as useGroceryHooks from '../hooks/useGrocery';

const sampleResult1: ProductMatchResult = {
  product_id: 'p1',
  product_name: 'Amul Fresh Paneer 200g',
  brand: 'Amul',
  category: 'Dairy',
  store_id: 's1',
  store_name: 'Demo QuickMart',
  price: 90.25,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.451,
  base_unit: 'g',
  similarity_score: 0.95,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 1,
  price_rank: 1,
};

const sampleResult2: ProductMatchResult = {
  product_id: 'p2',
  product_name: 'Mother Dairy Paneer 250g',
  brand: 'Mother Dairy',
  category: 'Dairy',
  store_id: 's2',
  store_name: 'Demo FreshBasket',
  price: 115.0,
  currency: 'INR',
  package_quantity: 250.0,
  package_unit: 'grams',
  unit_price: 0.46,
  base_unit: 'g',
  similarity_score: 0.90,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 2,
  price_rank: 2,
};

const sampleBestOption: BestProductOption = {
  product_id: 'p1',
  product_name: 'Amul Fresh Paneer 200g',
  store_id: 's1',
  store_name: 'Demo QuickMart',
  brand: 'Amul',
  category: 'Dairy',
  price: 90.25,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.451,
  base_unit: 'g',
  similarity_score: 0.95,
};

describe('GroceryPriceComparison Component', () => {
  it('1. Renders store comparison with store names, product names, package quantity and INR prices', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [sampleResult1, sampleResult2],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);

    expect(screen.getByTestId('grocery-compare-container')).toBeInTheDocument();
    expect(screen.getAllByText('Demo QuickMart').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Demo FreshBasket').length).toBeGreaterThan(0);
    expect(screen.getByText('Amul Fresh Paneer 200g')).toBeInTheDocument();
    expect(screen.getByText('Mother Dairy Paneer 250g')).toBeInTheDocument();
    expect(screen.getByText(/₹90.25/)).toBeInTheDocument();
    expect(screen.getByText(/₹115/)).toBeInTheDocument();
  });

  it('2. Renders normalized unit price when available', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult1],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    expect(screen.getByText(/₹0.45\/g|₹0.451\/g|₹0.451/)).toBeInTheDocument();
  });

  it('3. Visualizes comparison_mode === "unit_price" appropriately', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult1],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    const badge = screen.getByTestId('comparison-mode-badge');
    expect(badge).toHaveTextContent(/Normalized Unit Price/i);
  });

  it('4. Visualizes comparison_mode === "package_price" appropriately', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult1],
        best_option: sampleBestOption,
        comparison_mode: 'package_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    const badge = screen.getByTestId('comparison-mode-badge');
    expect(badge).toHaveTextContent(/Package Price/i);
  });

  it('5. Renders backend price_rank (#1 Price, #2 Price) correctly', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [sampleResult1, sampleResult2],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    expect(screen.getByTestId('price-rank-p1')).toHaveTextContent('#1 Price');
    expect(screen.getByTestId('price-rank-p2')).toHaveTextContent('#2 Price');
  });

  it('6. Highlights Best Value product using best_option.product_id', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [sampleResult1, sampleResult2],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    const item1 = screen.getByTestId('grocery-compare-item-p1');
    expect(item1.className).toContain('border-emerald-500');
    expect(screen.getByTestId('best-value-badge')).toBeInTheDocument();
  });

  it('7. Handles best_option === null safely without crash or false highlight', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [sampleResult1, sampleResult2],
        best_option: null,
        comparison_mode: null,
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    expect(screen.queryByTestId('best-value-badge')).not.toBeInTheDocument();
  });

  it('8. Renders empty state when total_matches === 0', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
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
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="dragonfruitxyz" />);
    expect(screen.getByTestId('grocery-compare-empty')).toBeInTheDocument();
    expect(screen.getByText('No grocery price comparisons found')).toBeInTheDocument();
  });

  it('9. Renders loading skeleton placeholders', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    expect(screen.getByTestId('grocery-compare-loading')).toBeInTheDocument();
  });

  it('10. Renders error state with retry button', () => {
    const refetchMock = vi.fn();
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: { message: 'Comparison service offline' },
      refetch: refetchMock,
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    expect(screen.getByTestId('grocery-compare-error')).toBeInTheDocument();
    expect(screen.getByText('Comparison service offline')).toBeInTheDocument();

    const retryBtn = screen.getByRole('button', { name: /retry comparison/i });
    fireEvent.click(retryBtn);
    expect(refetchMock).toHaveBeenCalledTimes(1);
  });

  it('11. Safe fallback behavior when comparison_mode is missing/null', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult1],
        best_option: sampleBestOption,
        comparison_mode: null, // missing comparison mode
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);
    // Component renders without crash and falls back safely
    expect(screen.getByTestId('grocery-compare-container')).toBeInTheDocument();
    expect(screen.getByText('Amul Fresh Paneer 200g')).toBeInTheDocument();
  });

  it('12. Selected state moves to clicked comparison card and preserves Best Value badge independently', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [sampleResult1, sampleResult2],
        best_option: sampleBestOption,
        comparison_mode: 'unit_price',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="paneer" />);

    const item1 = screen.getByTestId('grocery-compare-item-p1');
    const item2 = screen.getByTestId('grocery-compare-item-p2');

    // Initially best_option (p1) is selected (has border-emerald-500)
    expect(item1.className).toContain('border-emerald-500');
    expect(item2.className).not.toContain('border-emerald-500');
    expect(screen.getByTestId('best-value-badge')).toBeInTheDocument();

    // Click on item2
    fireEvent.click(item2);

    // Now item2 is selected, item1 is not selected, but best-value-badge is still rendered
    expect(item2.className).toContain('border-emerald-500');
    expect(item1.className).not.toContain('border-emerald-500');
    expect(screen.getByTestId('best-value-badge')).toBeInTheDocument();
  });

  it('13. Renders live provider response with PROVIDER_LIVE badge, Swiggy Instamart store and real product fields', () => {
    const liveProduct: ProductMatchResult = {
      product_id: 'swiggy_milk_1',
      product_name: 'Akshayakalpa Amrutha A2 Pasteurized Organic Milk',
      brand: 'Akshayakalpa',
      category: 'Dairy',
      store_id: 'store_swiggy',
      store_name: 'Swiggy Instamart',
      price: 49.0,
      currency: 'INR',
      package_quantity: 500.0,
      package_unit: 'ml',
      unit_price: 0.098,
      base_unit: 'ml',
      similarity_score: 0.96,
      matched_text: 'milk',
      match_status: 'matched',
      rank: 1,
      price_rank: 1,
      data_source_type: 'Swiggy Instamart',
      price_freshness: 'PROVIDER_LIVE',
    };

    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'milk',
        canonical_name: 'milk',
        threshold: 0.4,
        total_matches: 1,
        results: [liveProduct],
        best_option: liveProduct as unknown as BestProductOption,
        comparison_mode: 'package_price',
        data_source: 'live',
        price_freshness: 'PROVIDER_LIVE',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="milk" live_mode={true} />);

    // Verify Live Price badge
    expect(screen.getByText(/LIVE PRICE/i)).toBeInTheDocument();

    // Verify Live Product Details rendered directly from results
    expect(screen.getByText('Akshayakalpa Amrutha A2 Pasteurized Organic Milk')).toBeInTheDocument();
    expect(screen.getByText('₹49')).toBeInTheDocument();
    expect(screen.getAllByText('Swiggy Instamart').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Akshayakalpa/i).length).toBeGreaterThanOrEqual(1);
  });

  it('14. Passes live_mode prop to useGroceryCompare hook', () => {
    const hookSpy = vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="milk" live_mode={true} limit={8} />);

    expect(hookSpy).toHaveBeenCalledWith({
      ingredient: 'milk',
      limit: 8,
      threshold: undefined,
      live_mode: true,
    });
  });

  it('15. Renders Demo Dataset badge in demo mode and does not label demo data as LIVE PRICE', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryCompare').mockReturnValue({
      data: {
        ingredient_text: 'milk',
        canonical_name: 'milk',
        threshold: 0.4,
        total_matches: 1,
        results: [sampleResult1],
        best_option: sampleBestOption,
        comparison_mode: 'package_price',
        data_source: 'demo',
        price_freshness: 'DEMO',
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryCompare>);

    render(<GroceryPriceComparison ingredient="milk" live_mode={false} />);

    // Verify Demo Dataset badge is rendered
    expect(screen.getByText(/Demo Dataset/i)).toBeInTheDocument();
    // Verify LIVE PRICE is NOT rendered
    expect(screen.queryByText(/LIVE PRICE/i)).not.toBeInTheDocument();
  });
});
