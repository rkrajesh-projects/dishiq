import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from 'react-error-boundary';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { AppRoutes } from './routes/AppRoutes';
import { AuthProvider } from './context/AuthContext';
import { ErrorState } from './components/common/ErrorState';
import { queryClient } from './api/queryClient';

function ErrorFallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-cream-100 p-4">
      <ErrorState
        title="Application Error"
        message="A rendering error occurred in the DishIQ user interface."
        onRetry={resetErrorBoundary}
      />
    </div>
  );
}

function handleBoundaryError(error: Error, info: React.ErrorInfo) {
  // Log to console so the exact component and stack are visible in DevTools.
  console.error('[DishIQ ErrorBoundary]', error, info.componentStack ?? '(no stack available)');
}

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary FallbackComponent={ErrorFallback} onError={handleBoundaryError}>
        <AuthProvider>
        <BrowserRouter>
          <div className="min-h-screen flex flex-col justify-between bg-cream-100 text-brand-dark">
            <Header />
            <div className="flex-grow">
              <AppRoutes />
            </div>
            <Footer />
          </div>
        </BrowserRouter>
        </AuthProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
};

export default App;
