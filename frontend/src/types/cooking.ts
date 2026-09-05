export interface CookingSession {
  id: string;
  user_id: string;
  recipe_id: string;
  current_step: number;
  status: 'active' | 'paused' | 'completed';
  started_at: string;
  completed_at: string | null;
  notes: string | null;
}

export interface CookingSessionCreate {
  recipe_id: string;
  notes?: string;
}

export interface CookingSessionUpdate {
  current_step?: number;
  status?: 'active' | 'paused' | 'completed';
  notes?: string;
  completed_at?: string;
}
