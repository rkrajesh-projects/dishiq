export interface CookingSession {
  id: string;
  user_id: string;
  recipe_id: string;
  current_step: number;
  status: 'active' | 'paused' | 'completed';
  started_at: string;
  updated_at?: string | null;
  completed_at: string | null;
  notes: string | null;
  servings?: number | null;
  prepared_ingredients?: string[] | null;
}

export interface CookingSessionCreate {
  recipe_id: string;
  notes?: string;
  servings?: number;
}

export interface CookingSessionUpdate {
  current_step?: number;
  status?: 'active' | 'paused' | 'completed';
  notes?: string;
  servings?: number;
  prepared_ingredients?: string[];
  completed_at?: string;
}

export interface PreparationItem {
  id: string;
  ingredient_id?: string | null;
  name: string;
  raw_text: string;
  quantity?: number | null;
  scaled_quantity?: number | null;
  unit?: string | null;
  preparation_note?: string | null;
  category?: string | null;
  is_prepared: boolean;
  to_taste: boolean;
}

export interface PreparationChecklist {
  session_id: string;
  recipe_id: string;
  recipe_name: string;
  servings: number;
  base_servings: number;
  scale_factor: number;
  total_ingredients: number;
  prepared_count: number;
  all_prepared: boolean;
  items: PreparationItem[];
}

export type TimerStatus = 'idle' | 'running' | 'paused' | 'completed' | 'cancelled';

export interface CookingTimerEntity {
  id: string;
  user_id: string;
  cooking_session_id?: string | null;
  recipe_id?: string | null;
  step_index?: number | null;
  label: string;
  duration_seconds: number;
  remaining_seconds: number;
  status: TimerStatus;
  started_at?: string | null;
  ends_at?: string | null;
  paused_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CookingTimerCreatePayload {
  label: string;
  duration_seconds: number;
  step_index?: number | null;
  cooking_session_id?: string | null;
  recipe_id?: string | null;
  auto_start?: boolean;
}

export interface CompanionMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface CompanionChatRequest {
  cooking_session_id: string;
  message: string;
  step_index?: number;
  conversation_history?: CompanionMessage[];
}

export interface CompanionChatResponse {
  reply: string;
  response_mode: 'llm' | 'deterministic_fallback';
  provider?: string | null;
  model?: string | null;
  suggested_actions: string[];
  related_step?: number | null;
  disclaimer: string;
}
