import apiClient from './client';
import { RecommendedRecipe, PaginatedResponse, RecipeDetail } from '../types';

export interface RecipeFilters {
  cuisines: string[];
  dietary_types: string[];
}

export interface SearchRecipeParams {
  q?: string;
  cuisine?: string;
  dietary_type?: string;
  max_time?: number;
  min_rating?: number;
  sort_by?: string;
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

export const getRecipeFilters = async (): Promise<RecipeFilters> => {
  const response = await apiClient.get<RecipeFilters>('/recipes/filters');
  return response.data;
};

export const getRecipeByName = async (name: string): Promise<RecipeDetail> => {

  const response = await apiClient.get<RecipeDetail>(`/recipes/by-name?name=${encodeURIComponent(name)}`);
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

// ── ML API ──────────────────────────────────────────────────────────────────

export interface ClusterInfo {
  cluster_id: number;
  description: string;
  recipe_count: number;
}

export interface ClustersResponse {
  clusters: ClusterInfo[];
  model: string;
  algorithm: string;
  silhouette_score?: number;
}

export interface SimilarRecipesResponse {
  recipe_id: string;
  cluster_id: number | null;
  cluster_description: string;
  similar_recipe_ids: string[];
  model: string;
}

export interface SuitabilityResponse {
  recipe_id: string;
  suitability_score: number;
  model: string;
  note: string;
}

export const getRecipeClusters = async (): Promise<ClustersResponse> => {
  const response = await apiClient.get<ClustersResponse>('/ml/clusters');
  return response.data;
};

export const getSimilarRecipes = async (recipeId: string, limit = 6): Promise<SimilarRecipesResponse> => {
  const response = await apiClient.get<SimilarRecipesResponse>(`/ml/similar-recipes/${recipeId}`, {
    params: { limit },
  });
  return response.data;
};

export const getMLModelInfo = async (): Promise<Record<string, any>> => {
  const response = await apiClient.get('/ml/model-info');
  return response.data;
};
