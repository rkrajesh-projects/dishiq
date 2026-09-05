import apiClient from './client';
import { RecommendedRecipe, PaginatedResponse, RecipeDetail } from '../types';

export interface SearchRecipeParams {
  q?: string;
  cuisine?: string;
  dietary_type?: string;
  max_time?: number;
  ingredient?: string;
  page?: number;
  page_size?: number;
}

export const searchRecipes = async (params: SearchRecipeParams): Promise<PaginatedResponse<RecommendedRecipe>> => {
  const sanitizedParams = {
    ...params,
    page_size: params.page_size ? Math.min(params.page_size, 50) : undefined,
  };
  const response = await apiClient.get<PaginatedResponse<RecommendedRecipe>>('/recipes/search', { params: sanitizedParams });
  return response.data;
};

export const getRecipeRecommendations = async (payload: {
  query?: string;
  dietary_type?: string;
  max_time?: number;
  pantry_ingredients?: string[];
  limit?: number;
}) => {
  const response = await apiClient.post('/recommendations/recipes', payload);
  return response.data;
};

export const getRecipe = async (recipeId: string): Promise<RecipeDetail> => {
  const response = await apiClient.get<RecipeDetail>(`/recipes/${recipeId}`);
  return response.data;
};

export const submitRecipeFeedback = async (
  recipeId: string,
  payload: { rating: number; difficulty: string; notes?: string }
): Promise<any> => {
  const response = await apiClient.post(`/recipes/${recipeId}/feedback`, payload);
  return response.data;
};
