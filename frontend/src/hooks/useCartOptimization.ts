/**
 * DishIQ Phase 7 — Cart Optimization Hook
 * React Query hooks for cart comparison and optimization API calls.
 */
import { useMutation } from '@tanstack/react-query';
import { compareCart, optimizeCart } from '../api/grocery';
import { CartCompareRequest, CartCompareResponse, CartOptimizeResponse } from '../types';

export const useCartCompare = (liveMode: boolean = false) => {
  return useMutation<CartCompareResponse, Error, CartCompareRequest>({
    mutationFn: (request) => compareCart(request, liveMode),
  });
};

export const useCartOptimize = (liveMode: boolean = false) => {
  return useMutation<CartOptimizeResponse, Error, CartCompareRequest>({
    mutationFn: (request) => optimizeCart(request, liveMode),
  });
};
