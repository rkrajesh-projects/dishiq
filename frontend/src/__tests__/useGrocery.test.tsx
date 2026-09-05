import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useGroceryMatch, useGroceryCompare } from '../hooks/useGrocery';
import * as apiModule from '../api/grocery';

vi.mock('../api/grocery', () => ({
  matchGroceryProducts: vi.fn(),
  compareGroceryPrices: vi.fn(),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useGrocery custom hooks query enablement', () => {
  it('1. useGroceryMatch is disabled when ingredient is empty', () => {
    const { result } = renderHook(() => useGroceryMatch({ ingredient: '' }), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(true);
    expect(result.current.fetchStatus).toBe('idle');
    expect(apiModule.matchGroceryProducts).not.toHaveBeenCalled();
  });

  it('2. useGroceryMatch is disabled when ingredient is whitespace-only', () => {
    const { result } = renderHook(() => useGroceryMatch({ ingredient: '   ' }), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(true);
    expect(result.current.fetchStatus).toBe('idle');
    expect(apiModule.matchGroceryProducts).not.toHaveBeenCalled();
  });

  it('3. useGroceryMatch is enabled when ingredient is valid', () => {
    vi.mocked(apiModule.matchGroceryProducts).mockResolvedValue({
      ingredient_text: 'paneer',
      canonical_name: 'paneer',
      threshold: 0.4,
      total_matches: 0,
      results: [],
      best_option: null,
      comparison_mode: null,
    });

    const { result } = renderHook(() => useGroceryMatch({ ingredient: 'paneer' }), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('fetching');
  });

  it('4. useGroceryCompare is disabled when ingredient is empty', () => {
    const { result } = renderHook(() => useGroceryCompare({ ingredient: '' }), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(true);
    expect(result.current.fetchStatus).toBe('idle');
    expect(apiModule.compareGroceryPrices).not.toHaveBeenCalled();
  });

  it('5. useGroceryCompare is disabled when ingredient is whitespace-only', () => {
    const { result } = renderHook(() => useGroceryCompare({ ingredient: '  \n  ' }), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(true);
    expect(result.current.fetchStatus).toBe('idle');
    expect(apiModule.compareGroceryPrices).not.toHaveBeenCalled();
  });
});
