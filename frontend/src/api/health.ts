import apiClient from './client';
import { HealthResponse } from '../types';

export const fetchHealthStatus = async (): Promise<HealthResponse> => {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
};
