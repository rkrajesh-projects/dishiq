import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const customError = {
      message: error.response?.data?.error?.message || error.message || 'An unexpected API error occurred',
      status: error.response?.status || 500,
      code: error.response?.data?.error?.code || 'UNKNOWN_ERROR',
    };
    return Promise.reject(customError);
  }
);

export default apiClient;
