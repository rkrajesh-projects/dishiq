import apiClient from './client';
import {
  CookingSession,
  CookingSessionCreate,
  CookingSessionUpdate,
  PreparationChecklist,
  CookingTimerEntity,
  CookingTimerCreatePayload,
  CompanionChatRequest,
  CompanionChatResponse,
} from '../types/cooking';

export const startCookingSession = async (
  recipeId: string,
  notes?: string,
  servings?: number
): Promise<CookingSession> => {
  const payload: CookingSessionCreate = {
    recipe_id: recipeId,
    notes,
    servings,
  };
  const response = await apiClient.post<CookingSession>('/cooking/sessions', payload);
  return response.data;
};

export const getCookingSession = async (sessionId: string): Promise<CookingSession> => {
  const response = await apiClient.get<CookingSession>(`/cooking/sessions/${sessionId}`);
  return response.data;
};

export const updateCookingSession = async (
  sessionId: string,
  payload: CookingSessionUpdate
): Promise<CookingSession> => {
  const response = await apiClient.put<CookingSession>(`/cooking/sessions/${sessionId}`, payload);
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

export const pauseCookingSession = async (sessionId: string): Promise<CookingSession> => {
  const response = await apiClient.post<CookingSession>(`/cooking/sessions/${sessionId}/pause`);
  return response.data;
};

export const resumeCookingSession = async (sessionId: string): Promise<CookingSession> => {
  const response = await apiClient.post<CookingSession>(`/cooking/sessions/${sessionId}/resume`);
  return response.data;
};

export const completeCookingSession = async (sessionId: string): Promise<CookingSession> => {
  const response = await apiClient.post<CookingSession>(`/cooking/sessions/${sessionId}/complete`);
  return response.data;
};

export const getActiveCookingSession = async (recipeId?: string): Promise<CookingSession | null> => {
  const params = recipeId ? { recipe_id: recipeId } : undefined;
  const response = await apiClient.get<CookingSession | null>('/cooking/sessions/active', { params });
  return response.data;
};

export const getPreparationChecklist = async (sessionId: string): Promise<PreparationChecklist> => {
  const response = await apiClient.get<PreparationChecklist>(`/cooking/sessions/${sessionId}/preparation-checklist`);
  return response.data;
};

export const updatePreparedIngredients = async (
  sessionId: string,
  preparedIngredients: string[]
): Promise<CookingSession> => {
  const response = await apiClient.put<CookingSession>(`/cooking/sessions/${sessionId}/prepared-ingredients`, {
    prepared_ingredients: preparedIngredients,
  });
  return response.data;
};

// ---------------------------------------------------------------------------
// Phase 11 — Cooking Timers API
// ---------------------------------------------------------------------------

export const createCookingTimer = async (
  payload: CookingTimerCreatePayload
): Promise<CookingTimerEntity> => {
  const response = await apiClient.post<CookingTimerEntity>('/cooking/timers', payload);
  return response.data;
};

export const listCookingTimers = async (params?: {
  cooking_session_id?: string;
  recipe_id?: string;
  status?: string;
}): Promise<CookingTimerEntity[]> => {
  const response = await apiClient.get<CookingTimerEntity[]>('/cooking/timers', { params });
  return response.data;
};

export const getCookingTimer = async (timerId: string): Promise<CookingTimerEntity> => {
  const response = await apiClient.get<CookingTimerEntity>(`/cooking/timers/${timerId}`);
  return response.data;
};

export const startCookingTimer = async (timerId: string): Promise<CookingTimerEntity> => {
  const response = await apiClient.post<CookingTimerEntity>(`/cooking/timers/${timerId}/start`);
  return response.data;
};

export const pauseCookingTimer = async (timerId: string): Promise<CookingTimerEntity> => {
  const response = await apiClient.post<CookingTimerEntity>(`/cooking/timers/${timerId}/pause`);
  return response.data;
};

export const resumeCookingTimer = async (timerId: string): Promise<CookingTimerEntity> => {
  const response = await apiClient.post<CookingTimerEntity>(`/cooking/timers/${timerId}/resume`);
  return response.data;
};

export const cancelCookingTimer = async (timerId: string): Promise<CookingTimerEntity> => {
  const response = await apiClient.post<CookingTimerEntity>(`/cooking/timers/${timerId}/cancel`);
  return response.data;
};

export const resetCookingTimer = async (timerId: string): Promise<CookingTimerEntity> => {
  const response = await apiClient.post<CookingTimerEntity>(`/cooking/timers/${timerId}/reset`);
  return response.data;
};

export const deleteCookingTimer = async (timerId: string): Promise<void> => {
  await apiClient.delete(`/cooking/timers/${timerId}`);
};

export const askCookingCompanion = async (
  payload: CompanionChatRequest
): Promise<CompanionChatResponse> => {
  const response = await apiClient.post<CompanionChatResponse>('/cooking/companion/chat', payload);
  return response.data;
};
