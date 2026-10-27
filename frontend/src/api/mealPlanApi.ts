/**
 * DishIQ Phase 9 — Meal Planning & Shopping Lists API Client
 */
import apiClient from './client';
import {
  MealPlan,
  MealPlanCreate,
  MealPlanUpdate,
  MealPlanItem,
  MealPlanItemCreate,
  MealPlanItemUpdate,
  ShoppingList,
  ShoppingListItem,
  ShoppingListItemCreate,
  ShoppingListItemUpdate,
  ShoppingListGenerateRequest,
  ShoppingListGroceryComparison,
} from '../types/meal_plan';

// Meal Plans
export const getMealPlans = async (): Promise<MealPlan[]> => {
  const response = await apiClient.get<MealPlan[]>('/meal-plans');
  return response.data;
};

export const getMealPlan = async (id: string): Promise<MealPlan> => {
  const response = await apiClient.get<MealPlan>(`/meal-plans/${id}`);
  return response.data;
};

export const createMealPlan = async (data: MealPlanCreate): Promise<MealPlan> => {
  const response = await apiClient.post<MealPlan>('/meal-plans', data);
  return response.data;
};

export const updateMealPlan = async (id: string, data: MealPlanUpdate): Promise<MealPlan> => {
  const response = await apiClient.put<MealPlan>(`/meal-plans/${id}`, data);
  return response.data;
};

export const deleteMealPlan = async (id: string): Promise<void> => {
  await apiClient.delete(`/meal-plans/${id}`);
};

export const addMealToPlan = async (
  planId: string,
  data: MealPlanItemCreate
): Promise<MealPlanItem> => {
  const response = await apiClient.post<MealPlanItem>(`/meal-plans/${planId}/meals`, data);
  return response.data;
};

export const updatePlannedMeal = async (
  planId: string,
  mealId: string,
  data: MealPlanItemUpdate
): Promise<MealPlanItem> => {
  const response = await apiClient.put<MealPlanItem>(
    `/meal-plans/${planId}/meals/${mealId}`,
    data
  );
  return response.data;
};

export const removePlannedMeal = async (planId: string, mealId: string): Promise<void> => {
  await apiClient.delete(`/meal-plans/${planId}/meals/${mealId}`);
};

export const generateShoppingList = async (
  planId: string,
  data: ShoppingListGenerateRequest = { deduct_pantry: true }
): Promise<ShoppingList> => {
  const response = await apiClient.post<ShoppingList>(
    `/meal-plans/${planId}/shopping-list`,
    data
  );
  return response.data;
};

// Shopping Lists
export const getShoppingLists = async (): Promise<ShoppingList[]> => {
  const response = await apiClient.get<ShoppingList[]>('/shopping-lists');
  return response.data;
};

export const createShoppingList = async (
  name: string = 'My Shopping List',
  mealPlanId?: string
): Promise<ShoppingList> => {
  const response = await apiClient.post<ShoppingList>('/shopping-lists', {
    name,
    meal_plan_id: mealPlanId,
  });
  return response.data;
};

export const getShoppingList = async (id: string): Promise<ShoppingList> => {
  const response = await apiClient.get<ShoppingList>(`/shopping-lists/${id}`);
  return response.data;
};

export const addManualShoppingItem = async (
  listId: string,
  data: ShoppingListItemCreate
): Promise<ShoppingListItem> => {
  const response = await apiClient.post<ShoppingListItem>(
    `/shopping-lists/${listId}/items`,
    data
  );
  return response.data;
};

export const updateShoppingListItem = async (
  listId: string,
  itemId: string,
  data: ShoppingListItemUpdate
): Promise<ShoppingListItem> => {
  const response = await apiClient.patch<ShoppingListItem>(
    `/shopping-lists/${listId}/items/${itemId}`,
    data
  );
  return response.data;
};

export const deleteShoppingListItem = async (
  listId: string,
  itemId: string
): Promise<void> => {
  await apiClient.delete(`/shopping-lists/${listId}/items/${itemId}`);
};

export const getShoppingListGroceryComparison = async (
  listId: string
): Promise<ShoppingListGroceryComparison> => {
  const response = await apiClient.get<ShoppingListGroceryComparison>(
    `/shopping-lists/${listId}/grocery-comparison`
  );
  return response.data;
};
