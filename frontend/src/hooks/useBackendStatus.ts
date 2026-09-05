import { useQuery } from '@tanstack/react-query';
import { fetchHealthStatus } from '../api/health';

export const useBackendStatus = () => {
  const { data, isError, isPending, refetch } = useQuery({
    queryKey: ['backend-health'],
    queryFn: fetchHealthStatus,
    refetchInterval: 15000, // Poll health every 15s
  });

  const isConnected = !isError && !!data && data.status === 'ok';

  return {
    isConnected,
    isPending,
    isError,
    data,
    refetch,
  };
};

