export interface HealthResponse {
  status: string;
  application: string;
  version: string;
}

export interface Recipe {
  id: string;
  name: string;
  description: string;
  cuisine: string;
  dietary_type: string;
  preparation_minutes: number;
  cooking_minutes: number;
  servings: number;
  source_name: string;
  average_rating: number;
  created_at: string;
  score?: number;
  explanations?: string[];
}

export interface RecommendedRecipe extends Recipe {
  score: number;
  explanations: string[];
}

export interface RecipeIngredientRead {
  id: string;
  ingredient: {
    id: string;
    canonical_name: string;
    category: string;
    default_unit: string;
  };
  raw_text: string;
  quantity: number;
  unit: string;
  preparation_note: string | null;
}

export interface RecipeStepRead {
  step_number: number;
  text: string;
  action_type: string;
  timing_minutes?: number | null;
  temperature?: string | null;
  equipment?: string[];
  ingredients?: string[];
}

export interface RecipeDetail extends Recipe {
  instructions: string[];
  structured_instructions?: RecipeStepRead[] | null;
  source_url?: string | null;
  author?: string | null;
  source_license?: string | null;
  region?: string | null;
  state?: string | null;
  original_name?: string | null;
  is_indian_recipe?: boolean | null;
  verification_status?: string | null;
  ingredients: RecipeIngredientRead[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface GroceryStore {
  id: string;
  name: string;
  store_type: string;
  city: string;
  is_demo_store: boolean;
  created_at: string;
}

export interface ProductPrice {
  id: string;
  price: number;
  currency: string;
  delivery_fee: number;
  observed_at: string;
  data_source_type: string;
}

export interface GroceryProduct {
  id: string;
  store_id: string;
  name: string;
  normalized_name: string;
  brand: string;
  package_quantity: number;
  package_unit: string;
  category: string;
  in_stock: boolean;
  prices: ProductPrice[];
}

export * from './grocery';
export * from './cart';
export * from './cooking';
export * from './pantry';
export * from './profile';

export interface RecipeFeedbackInput {
  rating: number;
  difficulty: string;
  notes?: string;
}

export interface RecipeFeedback {
  id: string;
  user_id: string;
  recipe_id: string;
  rating: number;
  difficulty: string;
  notes?: string;
  created_at: string;
}
