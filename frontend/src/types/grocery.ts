/**
 * DishIQ Phase 6.4.1 — Grocery Matching & Price Comparison Types
 * Mirrors backend Pydantic schemas in backend/app/product_matching/schemas.py
 */

export interface BestProductOption {
  product_id: string;
  product_name: string;
  store_id: string | null;
  store_name: string | null;
  brand: string | null;
  category: string | null;
  price: number;
  currency: 'INR' | string;
  package_quantity: number | null;
  package_unit: string | null;
  unit_price: number | null;
  base_unit: string | null;
  similarity_score: number;
}

export interface ProductMatchResult {
  product_id: string;
  product_name: string;
  brand: string | null;
  category: string | null;
  store_id: string | null;
  store_name: string | null;
  price: number | null;
  currency: 'INR' | string;
  package_quantity: number | null;
  package_unit: string | null;
  unit_price: number | null;
  base_unit: string | null;
  similarity_score: number;
  matched_text: string;
  match_status: 'matched' | 'low_confidence' | string;
  rank: number;
  price_rank: number | null;
}

export interface MatchIngredientsResponse {
  ingredient_text: string;
  canonical_name: string;
  threshold: number;
  total_matches: number;
  results: ProductMatchResult[];
  best_option: BestProductOption | null;
  comparison_mode: 'unit_price' | 'package_price' | string | null;
}

export type GroceryCompareResponse = MatchIngredientsResponse;

export interface MatchGroceryParams {
  ingredient: string;
  limit?: number;
  threshold?: number;
}

export type CompareGroceryParams = MatchGroceryParams;
