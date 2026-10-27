import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Generate safe client-side correlation ID if not provided
  if (config.headers && !config.headers['X-Request-ID']) {
    const correlationId = 'dishiq-' + Math.random().toString(36).substring(2, 10);
    config.headers['X-Request-ID'] = correlationId;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
    const requestId =
      error.response?.headers?.['x-request-id'] ||
      error.config?.headers?.['X-Request-ID'];

    const customError = {
      message:
        error.response?.data?.error?.message ||
        error.response?.data?.detail ||
        error.message ||
        'An unexpected API error occurred',
      status: error.response?.status || 500,
      code: error.response?.data?.error?.code || 'UNKNOWN_ERROR',
      requestId: requestId || undefined,
    };
    return Promise.reject(customError);
  }
);

export default apiClient;
