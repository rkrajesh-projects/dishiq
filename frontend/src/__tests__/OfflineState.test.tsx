import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { Header } from '../components/layout/Header';
import * as healthApi from '../api/health';

vi.mock('../api/health', () => ({
  fetchHealthStatus: vi.fn(),
}));

describe('OfflineState Component Integration', () => {
  it('displays "Backend Offline" badge when health check API fails', async () => {
    (healthApi.fetchHealthStatus as any).mockRejectedValueOnce(new Error('Network error'));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Backend Offline')).toBeInTheDocument();
    });
  });
});
