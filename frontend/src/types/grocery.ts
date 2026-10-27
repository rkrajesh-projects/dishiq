/**
 * DishIQ Phase 6.4.1 & Phase 8 — Grocery Matching & Price Comparison Types
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
  standardized_unit_price?: number | null;
  standardized_unit?: string | null;
  savings_amount?: number | null;
  savings_percent?: number | null;
  reference_product_name?: string | null;
  comparison_notes?: string | null;
  mrp?: number | null;
  discount?: number | null;
  location?: string | null;
  availability?: boolean;
  data_source_type?: string | null;
  price_freshness?: string | null;
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
  standardized_unit_price?: number | null;
  standardized_unit?: string | null;
  is_comparable?: boolean;
  comparison_notes?: string | null;
  savings_amount?: number | null;
  savings_percent?: number | null;
  reference_product_name?: string | null;
  mrp?: number | null;
  discount?: number | null;
  location?: string | null;
  availability?: boolean;
  data_source_type?: string | null;
  price_freshness?: string | null;
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
  data_source?: 'live' | 'demo' | string;
  price_freshness?: 'PROVIDER_LIVE' | 'LIVE' | 'CACHED' | 'DEMO' | 'UNKNOWN' | string;
}

export type GroceryCompareResponse = MatchIngredientsResponse;

export interface MatchGroceryParams {
  ingredient: string;
  limit?: number;
  threshold?: number;
  sort_by?: string;
  live_mode?: boolean;
  pincode?: string;
}

export type CompareGroceryParams = MatchGroceryParams;
