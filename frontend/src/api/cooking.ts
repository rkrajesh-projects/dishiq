import apiClient from './client';
import { CookingSession } from '../types';

export const startCookingSession = async (recipeId: string, notes?: string): Promise<CookingSession> => {
  const response = await apiClient.post<CookingSession>('/cooking/sessions', {
    recipe_id: recipeId,
    notes,
  });
  return response.data;
};

export const getCookingSession = async (sessionId: string): Promise<CookingSession> => {
  const response = await apiClient.get<CookingSession>(`/cooking/sessions/${sessionId}`);
  return response.data;
};

export const nextCookingStep = async (sessionId: string): Promise<CookingSession> => {
  const response = await apiClient.post<CookingSession>(`/cooking/sessions/${sessionId}/next`);
  return response.data;
};

export const previousCookingStep = async (sessionId: string): Promise<CookingSession> => {
  const response = await apiClient.post<CookingSession>(`/cooking/sessions/${sessionId}/previous`);
  return response.data;
};

export const completeCookingSession = async (sessionId: string): Promise<CookingSession> => {
  const response = await apiClient.post<CookingSession>(`/cooking/sessions/${sessionId}/complete`);
  return response.data;
};

export const getActiveCookingSession = async (): Promise<CookingSession | null> => {
  const response = await apiClient.get<CookingSession | null>('/cooking/sessions/active');
  return response.data;
};
