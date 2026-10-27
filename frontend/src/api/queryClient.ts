import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (failureCount, error: any) => {
        if (failureCount >= 2) return false;
        const status = error?.status || error?.response?.status;
        // Do not retry on client-side errors (auth, forbidden, not found, validation)
        if (status === 401 || status === 403 || status === 404 || status === 422) {
          return false;
        }
        return true;
      },
    },
  },
});

export default queryClient;
