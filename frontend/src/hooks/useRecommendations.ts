import { useQuery } from '@tanstack/react-query';
import { getRecipeRecommendations } from '../api/recipes';
import { RecommendedRecipe } from '../types';

export const useRecommendations = (
  payload: {
    query?: string;
    dietary_type?: string;
    max_time?: number;
    pantry_ingredients?: string[];
    limit?: number;
  },
  enabled: boolean = true
) => {
  return useQuery<{ recommendations: RecommendedRecipe[]; total: number }, Error>({
    queryKey: ['recipe-recommendations', payload],
    queryFn: () => getRecipeRecommendations(payload),
    enabled,
    staleTime: 30_000,
  });
};
