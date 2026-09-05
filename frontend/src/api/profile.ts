import apiClient from './client';
import { UserProfile, ProfileUpdatePayload } from '../types';

/** GET /api/profile — fetch current user's profile and preferences */
export const getProfile = async (): Promise<UserProfile> => {
  const response = await apiClient.get<UserProfile>('/profile');
  return response.data;
};

/** PATCH /api/profile — update profile details or preferences */
export const updateProfile = async (body: ProfileUpdatePayload): Promise<UserProfile> => {
  const response = await apiClient.patch<UserProfile>('/profile', body);
  return response.data;
};
