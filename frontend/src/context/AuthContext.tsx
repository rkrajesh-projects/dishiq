import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { queryClient } from '../api/queryClient';

export interface UserRead {
  id: string;
  email: string;
  full_name: string;
}

export interface AuthContextType {
  token: string | null;
  user: UserRead | null;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [user, setUser] = useState<UserRead | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCurrentUser = useCallback(async (authToken: string) => {
    try {
      const response = await apiClient.get<UserRead>('/auth/me', {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      setUser(response.data);
      return response.data;
    } catch {
      // Invalid or expired token: clear credentials
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      return null;
    }
  }, []);

  // Validate and restore session on mount or token change
  useEffect(() => {
    let isMounted = true;
    const initialToken = localStorage.getItem('token');
    if (initialToken) {
      fetchCurrentUser(initialToken).finally(() => {
        if (isMounted) setIsLoading(false);
      });
    } else {
      setIsLoading(false);
    }
    return () => {
      isMounted = false;
    };
  }, [fetchCurrentUser]);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    // Purge cached React Query data immediately so next account cannot see it
    queryClient.clear();
    // Notify server asynchronously
    apiClient.post('/auth/logout').catch(() => {});
  }, []);

  const login = useCallback(
    async (newToken: string) => {
      localStorage.setItem('token', newToken);
      setToken(newToken);
      await fetchCurrentUser(newToken);
    },
    [fetchCurrentUser]
  );

  // Automatically logout when 401 Unauthorized is intercepted
  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isLoading,
        login,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
