import { useQuery } from '@tanstack/react-query';
import { matchGroceryProducts, compareGroceryPrices } from '../api/grocery';
import { MatchGroceryParams, CompareGroceryParams } from '../types';

export const useGroceryMatch = (params: MatchGroceryParams) => {
  const cleanedIngredient = (params.ingredient || '').trim();
  const enabled = cleanedIngredient.length > 0;

  return useQuery({
    queryKey: ['grocery-match', cleanedIngredient, params.limit, params.threshold, params.live_mode],
    queryFn: () => matchGroceryProducts({ ...params, ingredient: cleanedIngredient }),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes cache
  });
};

export const useGroceryCompare = (params: CompareGroceryParams) => {
  const cleanedIngredient = (params.ingredient || '').trim();
  const enabled = cleanedIngredient.length > 0;

  return useQuery({
    queryKey: ['grocery-compare', cleanedIngredient, params.limit, params.threshold, params.live_mode],
    queryFn: () => compareGroceryPrices({ ...params, ingredient: cleanedIngredient }),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes cache
  });
};
