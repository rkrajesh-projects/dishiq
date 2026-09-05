import { describe, it, expect, vi } from 'vitest';
import apiClient from '../api/client';
import { fetchHealthStatus } from '../api/health';

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
  },
  apiClient: {
    get: vi.fn(),
  },
}));

describe('Health API Client', () => {
  it('calls /health endpoint and returns data', async () => {
    const mockHealthData = {
      status: 'ok',
      application: 'DishIQ',
      version: '1.0.0',
    };

    (apiClient.get as any).mockResolvedValueOnce({ data: mockHealthData });

    const result = await fetchHealthStatus();
    expect(apiClient.get).toHaveBeenCalledWith('/health');
    expect(result).toEqual(mockHealthData);
  });
});
