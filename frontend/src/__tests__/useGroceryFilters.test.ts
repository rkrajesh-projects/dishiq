import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGroceryFilters } from '../hooks/useGroceryFilters';
import { ProductMatchResult } from '../types';

const productA: ProductMatchResult = {
  product_id: 'p1',
  product_name: 'Cheap Paneer',
  brand: null,
  category: null,
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

const productB: ProductMatchResult = {
  product_id: 'p2',
  product_name: 'Expensive Paneer',
  brand: null,
  category: null,
  store_id: 's2',
  store_name: 'Demo FreshBasket',
  price: 130.0,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.65,
  base_unit: 'g',
  similarity_score: 0.80,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 2,
  price_rank: 2,
};

const productNoPrice: ProductMatchResult = {
  product_id: 'p3',
  product_name: 'No Price Paneer',
  brand: null,
  category: null,
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
  rank: 3,
  price_rank: null,
};

const productNoStore: ProductMatchResult = {
  product_id: 'p4',
  product_name: 'No Store Paneer',
  brand: null,
  category: null,
  store_id: 's4',
  store_name: null,
  price: 100.0,
  currency: 'INR',
  package_quantity: 200.0,
  package_unit: 'grams',
  unit_price: 0.50,
  base_unit: 'g',
  similarity_score: 0.85,
  matched_text: 'paneer',
  match_status: 'matched',
  rank: 4,
  price_rank: 4,
};

describe('useGroceryFilters Custom Hook', () => {
  it('1. Returns initial/default filter state', () => {
    const { result } = renderHook(() => useGroceryFilters({ results: [productA, productB] }));

    expect(result.current.selectedStore).toBe('all');
    expect(result.current.sortOption).toBe('default');
    expect(result.current.availableStores).toEqual(['Demo FreshBasket', 'Demo QuickMart']);
    expect(result.current.totalCount).toBe(2);
    expect(result.current.filteredCount).toBe(2);
    expect(result.current.filteredAndSortedResults).toEqual([productA, productB]);
  });

  it('2. Filters results by selected store', () => {
    const { result } = renderHook(() => useGroceryFilters({ results: [productA, productB] }));

    act(() => {
      result.current.setSelectedStore('Demo FreshBasket');
    });

    expect(result.current.selectedStore).toBe('Demo FreshBasket');
    expect(result.current.filteredCount).toBe(1);
    expect(result.current.filteredAndSortedResults).toEqual([productB]);
  });

  it('3. Sorts results by price ascending and descending', () => {
    const { result } = renderHook(() => useGroceryFilters({ results: [productB, productA] }));

    // Price Ascending (p1: 90, p2: 130)
    act(() => {
      result.current.setSortOption('price_asc');
    });
    expect(result.current.filteredAndSortedResults[0].product_id).toBe('p1');
    expect(result.current.filteredAndSortedResults[1].product_id).toBe('p2');

    // Price Descending (p2: 130, p1: 90)
    act(() => {
      result.current.setSortOption('price_desc');
    });
    expect(result.current.filteredAndSortedResults[0].product_id).toBe('p2');
    expect(result.current.filteredAndSortedResults[1].product_id).toBe('p1');
  });

  it('4. Resets store and sort options via resetFilters', () => {
    const { result } = renderHook(() => useGroceryFilters({ results: [productA, productB] }));

    act(() => {
      result.current.setSelectedStore('Demo QuickMart');
      result.current.setSortOption('price_desc');
    });

    expect(result.current.selectedStore).toBe('Demo QuickMart');
    expect(result.current.sortOption).toBe('price_desc');

    act(() => {
      result.current.resetFilters();
    });

    expect(result.current.selectedStore).toBe('all');
    expect(result.current.sortOption).toBe('default');
  });

  it('5. Handles empty and null results gracefully', () => {
    const { result: emptyResult } = renderHook(() => useGroceryFilters({ results: [] }));
    expect(emptyResult.current.availableStores).toEqual([]);
    expect(emptyResult.current.filteredAndSortedResults).toEqual([]);
    expect(emptyResult.current.totalCount).toBe(0);

    const { result: nullResult } = renderHook(() => useGroceryFilters({ results: null }));
    expect(nullResult.current.availableStores).toEqual([]);
    expect(nullResult.current.filteredAndSortedResults).toEqual([]);
    expect(nullResult.current.totalCount).toBe(0);
  });

  it('6. Handles null prices safely placing them at the bottom for both sorts', () => {
    const { result } = renderHook(() => useGroceryFilters({ results: [productNoPrice, productB, productA] }));

    // Price Ascending (p1: 90, p2: 130, p3: null)
    act(() => {
      result.current.setSortOption('price_asc');
    });
    expect(result.current.filteredAndSortedResults[2].product_id).toBe('p3');

    // Price Descending (p2: 130, p1: 90, p3: null)
    act(() => {
      result.current.setSortOption('price_desc');
    });
    expect(result.current.filteredAndSortedResults[2].product_id).toBe('p3');
  });

  it('7. Handles null store names safely', () => {
    const { result } = renderHook(() => useGroceryFilters({ results: [productA, productNoStore] }));

    // Does not include null store name in available stores dropdown list
    expect(result.current.availableStores).toEqual(['Demo QuickMart']);
    // But does display the item when filter is set to "All Stores"
    expect(result.current.filteredAndSortedResults.length).toBe(2);
  });

  it('8. Preserves original API order when sort option is Default Order', () => {
    const originalResults = [productB, productA, productNoPrice];
    const { result } = renderHook(() => useGroceryFilters({ results: originalResults }));

    act(() => {
      result.current.setSortOption('default');
    });

    expect(result.current.filteredAndSortedResults).toEqual(originalResults);
  });
});
