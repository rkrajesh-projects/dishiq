/**
 * DishIQ Phase 7 — Cart Optimization Hook
 * React Query hooks for cart comparison and optimization API calls.
 */
import { useMutation } from '@tanstack/react-query';
import { compareCart, optimizeCart } from '../api/grocery';
import { CartCompareRequest, CartCompareResponse, CartOptimizeResponse } from '../types';

export const useCartCompare = () => {
  return useMutation<CartCompareResponse, Error, CartCompareRequest>({
    mutationFn: compareCart,
  });
};

export const useCartOptimize = () => {
  return useMutation<CartOptimizeResponse, Error, CartCompareRequest>({
    mutationFn: optimizeCart,
  });
};
