import { useState, useMemo } from 'react';
import { ProductMatchResult } from '../types';

export type SortOption =
  | 'default'
  | 'price_asc'
  | 'price_desc'
  | 'similarity_desc'
  | 'similarity_asc';

export interface UseGroceryFiltersOptions {
  results: ProductMatchResult[] | null | undefined;
}

export function useGroceryFilters({ results }: UseGroceryFiltersOptions) {
  const [selectedStore, setSelectedStore] = useState<string>('all');
  const [sortOption, setSortOption] = useState<SortOption>('default');

  // Extract unique available store names from results
  const availableStores = useMemo(() => {
    if (!results || results.length === 0) return [];
    const storeSet = new Set<string>();
    results.forEach((r) => {
      if (r.store_name && r.store_name.trim()) {
        storeSet.add(r.store_name.trim());
      }
    });
    return Array.from(storeSet).sort();
  }, [results]);

  // Compute filtered & sorted product list
  const filteredAndSortedResults = useMemo(() => {
    if (!results || results.length === 0) return [];

    // 1. Filter by store
    let filtered = results;
    if (selectedStore !== 'all') {
      filtered = results.filter((r) => r.store_name?.trim() === selectedStore);
    }

    // 2. Sort
    if (sortOption === 'default') {
      return filtered;
    }

    const copy = [...filtered];
    copy.sort((a, b) => {
      if (sortOption === 'price_asc' || sortOption === 'price_desc') {
        const hasA = a.price !== null && a.price !== undefined && Number.isFinite(a.price);
        const hasB = b.price !== null && b.price !== undefined && Number.isFinite(b.price);

        if (!hasA && !hasB) return 0;
        if (!hasA) return 1;  // null price always sorted to the bottom
        if (!hasB) return -1; // null price always sorted to the bottom

        const priceA = a.price as number;
        const priceB = b.price as number;
        if (priceA === priceB) return 0;
        return sortOption === 'price_asc' ? priceA - priceB : priceB - priceA;
      }

      if (sortOption === 'similarity_desc' || sortOption === 'similarity_asc') {
        const simA = a.similarity_score ?? 0;
        const simB = b.similarity_score ?? 0;
        return sortOption === 'similarity_desc' ? simB - simA : simA - simB;
      }

      return 0;
    });

    return copy;
  }, [results, selectedStore, sortOption]);

  const resetFilters = () => {
    setSelectedStore('all');
    setSortOption('default');
  };

  return {
    selectedStore,
    setSelectedStore,
    sortOption,
    setSortOption,
    availableStores,
    filteredAndSortedResults,
    totalCount: results?.length || 0,
    filteredCount: filteredAndSortedResults.length,
    resetFilters,
  };
}
