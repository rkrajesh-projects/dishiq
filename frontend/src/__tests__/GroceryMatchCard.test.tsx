import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { GroceryMatchCard } from '../components/grocery/GroceryMatchCard';
import { GroceryMatchList } from '../components/grocery/GroceryMatchList';
import { ProductMatchResult } from '../types';
import * as useGroceryHooks from '../hooks/useGrocery';

const sampleMatch: ProductMatchResult = {
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

const sampleMatch2: ProductMatchResult = {
  ...sampleMatch,
  product_id: 'p2',
  product_name: 'Mother Dairy Paneer 250g',
  store_name: 'Demo FreshBasket',
  price: 115.0,
  unit_price: 0.46,
  price_rank: 2,
};

describe('GroceryMatchCard & GroceryMatchList UI Components', () => {
  it('1. Matched product renders product name, brand, and category', () => {
    render(<GroceryMatchCard match={sampleMatch} />);
    expect(screen.getByText('Amul Fresh Paneer 200g')).toBeInTheDocument();
    expect(screen.getByText('Amul')).toBeInTheDocument();
    expect(screen.getByText('Dairy')).toBeInTheDocument();
  });

  it('2. Product name and store name render correctly', () => {
    render(<GroceryMatchCard match={sampleMatch} />);
    expect(screen.getByText('Demo QuickMart')).toBeInTheDocument();
  });

  it('3. Similarity score renders as a user-friendly percentage', () => {
    render(<GroceryMatchCard match={sampleMatch} />);
    expect(screen.getByText('92% match')).toBeInTheDocument();
    expect(screen.getByText('#1 Match')).toBeInTheDocument();
  });

  it('4. Package price renders using ₹ INR symbol', () => {
    render(<GroceryMatchCard match={sampleMatch} />);
    expect(screen.getByText(/₹95/)).toBeInTheDocument();
    expect(screen.getByText('200 grams')).toBeInTheDocument();
  });

  it('5. Unit price renders correctly when available', () => {
    render(<GroceryMatchCard match={sampleMatch} />);
    expect(screen.getByText(/₹0.48\/g|₹0.475\/g|₹0.475/)).toBeInTheDocument();
  });

  it('6. Missing optional fields do not break rendering', () => {
    const minimalMatch: ProductMatchResult = {
      product_id: 'p2',
      product_name: 'Generic Tomatoes 500g',
      brand: null,
      category: null,
      store_id: null,
      store_name: null,
      price: null,
      currency: 'INR',
      package_quantity: null,
      package_unit: null,
      unit_price: null,
      base_unit: null,
      similarity_score: 0.85,
      matched_text: 'tomato',
      match_status: 'matched',
      rank: 2,
      price_rank: null,
    };

    render(<GroceryMatchCard match={minimalMatch} />);
    expect(screen.getByText('Generic Tomatoes 500g')).toBeInTheDocument();
    expect(screen.getByText('Price unavailable')).toBeInTheDocument();
    expect(screen.getByText('85% match')).toBeInTheDocument();
  });

  it('7. Low-confidence match is represented appropriately with caution styling', () => {
    const lowConfMatch: ProductMatchResult = {
      ...sampleMatch,
      product_id: 'p3',
      match_status: 'low_confidence',
      similarity_score: 0.35,
    };

    render(<GroceryMatchCard match={lowConfMatch} />);
    expect(screen.getByText('35% match')).toBeInTheDocument();
    const card = screen.getByTestId('grocery-match-card-p3');
    expect(card.className).toContain('border-amber-200');
  });

  it('8. Empty result state renders when total_matches === 0', () => {
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
    expect(screen.getByTestId('grocery-match-empty')).toBeInTheDocument();
    expect(screen.getByText('No matching grocery products found')).toBeInTheDocument();
  });

  it('9. Loading state renders skeleton placeholders', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);
    expect(screen.getByTestId('grocery-match-loading')).toBeInTheDocument();
  });

  it('10. Error state renders error card', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: { message: 'Network connection error' },
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);
    expect(screen.getByTestId('grocery-match-error')).toBeInTheDocument();
    expect(screen.getByText('Network connection error')).toBeInTheDocument();
  });

  it('11. Retry action button calls refetch() when clicked', () => {
    const refetchMock = vi.fn();
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: { message: 'Server unavailable' },
      refetch: refetchMock,
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);
    const retryBtn = screen.getByRole('button', { name: /retry search/i });
    fireEvent.click(retryBtn);
    expect(refetchMock).toHaveBeenCalledTimes(1);
  });

  it('12. Product matching best_option.product_id receives Best Value badge and lowest price label', () => {
    render(<GroceryMatchCard match={sampleMatch} isBestValue={true} isSelected={true} />);
    expect(screen.getByTestId('best-value-badge')).toBeInTheDocument();
    expect(screen.getByText('Best Value')).toBeInTheDocument();
    expect(screen.getByText('Lowest comparable price')).toBeInTheDocument();
    const card = screen.getByTestId('grocery-match-card-p1');
    expect(card.className).toContain('border-emerald-500');
  });

  it('13. Non-winning products do not receive the Best Value badge', () => {
    render(<GroceryMatchCard match={sampleMatch2} isBestValue={false} />);
    expect(screen.queryByTestId('best-value-badge')).not.toBeInTheDocument();
    expect(screen.queryByText('Best Value')).not.toBeInTheDocument();
    expect(screen.queryByText('Lowest comparable price')).not.toBeInTheDocument();
  });

  it('14. best_option === null renders no Best Value badge in GroceryMatchList', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [sampleMatch, sampleMatch2],
        best_option: null,
        comparison_mode: null,
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);
    expect(screen.queryByTestId('best-value-badge')).not.toBeInTheDocument();
  });

  it('15. Unknown best_option.product_id renders safely without crashing or false highlighting', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [sampleMatch, sampleMatch2],
        best_option: {
          product_id: 'unknown_p99',
          product_name: 'Unknown Product',
          store_id: null,
          store_name: null,
          brand: null,
          category: null,
          price: 50.0,
          currency: 'INR',
          package_quantity: null,
          package_unit: null,
          unit_price: null,
          base_unit: null,
          similarity_score: 0.99,
        },
        comparison_mode: null,
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);
    expect(screen.getByText('Amul Fresh Paneer 200g')).toBeInTheDocument();
    expect(screen.getByText('Mother Dairy Paneer 250g')).toBeInTheDocument();
    expect(screen.queryByTestId('best-value-badge')).not.toBeInTheDocument();
  });

  it('16. GroceryMatchList product card selection state and interactions', () => {
    vi.spyOn(useGroceryHooks, 'useGroceryMatch').mockReturnValue({
      data: {
        ingredient_text: 'paneer',
        canonical_name: 'paneer',
        threshold: 0.4,
        total_matches: 2,
        results: [sampleMatch, sampleMatch2],
        best_option: sampleMatch,
        comparison_mode: null,
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useGroceryHooks.useGroceryMatch>);

    render(<GroceryMatchList ingredient="paneer" />);

    const cardP1 = screen.getByTestId('grocery-match-card-p1');
    const cardP2 = screen.getByTestId('grocery-match-card-p2');

    expect(cardP1.className).toContain('border-emerald-500');
    expect(cardP2.className).not.toContain('border-emerald-500');
    expect(screen.getByTestId('best-value-badge')).toBeInTheDocument();

    fireEvent.click(cardP2);

    expect(cardP2.className).toContain('border-emerald-500');
    expect(cardP1.className).not.toContain('border-emerald-500');
    expect(screen.getByTestId('best-value-badge')).toBeInTheDocument();
  });
});
