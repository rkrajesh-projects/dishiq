export interface ProfilePreference {
  dietary_type: string;
  weekly_budget: number;
  household_size: number;
  disliked_ingredients: string[];
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  preference: ProfilePreference;
}

export interface ProfileUpdatePayload {
  full_name?: string;
  dietary_type?: string;
  weekly_budget?: number;
  household_size?: number;
}
