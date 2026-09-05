import apiClient from './client';
import {
  GroceryStore,
  GroceryProduct,
  PaginatedResponse,
  MatchIngredientsResponse,
  GroceryCompareResponse,
  MatchGroceryParams,
  CompareGroceryParams,
  CartCompareRequest,
  CartCompareResponse,
  CartOptimizeResponse,
} from '../types';

export const getStores = async (params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<GroceryStore>> => {
  const sanitizedParams = params
    ? {
        ...params,
        page_size: params.page_size ? Math.min(params.page_size, 50) : undefined,
      }
    : undefined;
  const response = await apiClient.get<PaginatedResponse<GroceryStore>>('/stores', { params: sanitizedParams });
  return response.data;
};

export const getProducts = async (params?: { store_id?: string; category?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<GroceryProduct>> => {
  const sanitizedParams = params
    ? {
        ...params,
        page_size: params.page_size ? Math.min(params.page_size, 50) : undefined,
      }
    : undefined;
  const response = await apiClient.get<PaginatedResponse<GroceryProduct>>('/products', { params: sanitizedParams });
  return response.data;
};

export const matchGroceryProducts = async (params: MatchGroceryParams): Promise<MatchIngredientsResponse> => {
  const trimmed = (params.ingredient || '').trim();
  if (!trimmed) {
    return {
      ingredient_text: '',
      canonical_name: '',
      threshold: params.threshold ?? 0.4,
      total_matches: 0,
      results: [],
      best_option: null,
      comparison_mode: null,
    };
  }
  const response = await apiClient.get<MatchIngredientsResponse>('/grocery/match', {
    params: {
      ...params,
      ingredient: trimmed,
    },
  });
  return response.data;
};

export const compareGroceryPrices = async (params: CompareGroceryParams): Promise<GroceryCompareResponse> => {
  const trimmed = (params.ingredient || '').trim();
  if (!trimmed) {
    return {
      ingredient_text: '',
      canonical_name: '',
      threshold: params.threshold ?? 0.4,
      total_matches: 0,
      results: [],
      best_option: null,
      comparison_mode: null,
    };
  }
  const response = await apiClient.get<GroceryCompareResponse>('/grocery/compare', {
    params: {
      ...params,
      ingredient: trimmed,
    },
  });
  return response.data;
};

export const compareCart = async (request: CartCompareRequest): Promise<CartCompareResponse> => {
  const response = await apiClient.post<CartCompareResponse>('/cart/compare', request);
  return response.data;
};

export const optimizeCart = async (request: CartCompareRequest): Promise<CartOptimizeResponse> => {
  const response = await apiClient.post<CartOptimizeResponse>('/cart/optimize', request);
  return response.data;
};
