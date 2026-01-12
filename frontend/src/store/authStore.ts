/**
 * Auth Store - Zustand
 * 
 * Global authentication state with JWT token management.
 * Handles login, logout, token refresh, and user session.
 * 
 * @module store/authStore
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { User, AuthResponse, LoginRequest, SubscriptionTier } from '@/types/auth';

// =============================================================================
// Types
// =============================================================================

export interface AuthStore {
  // State
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Computed getters
  tier: SubscriptionTier;
  isPremium: boolean;

  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  setTokens: (tokens: { access: string; refresh: string }) => void;
  setUser: (user: User | null) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  refreshAccessToken: () => Promise<void>;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Decode JWT token to extract payload
 */
function decodeToken(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Failed to decode token:', error);
    return null;
  }
}

/**
 * Check if token is expired
 */
function isTokenExpired(token: string): boolean {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return true;
  
  const expiryTime = decoded.exp * 1000; // Convert to milliseconds
  const now = Date.now();
  const bufferTime = 5 * 60 * 1000; // 5 minutes buffer
  
  return expiryTime - now < bufferTime;
}

// =============================================================================
// Store
// =============================================================================

export const useAuthStore = create<AuthStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,

        // Computed properties
        get tier() {
          return get().user?.subscription_tier || 'BASIC';
        },

        get isPremium() {
          const user = get().user;
          if (!user) return false;
          
          // Check is_premium flag and expiry
          if (!user.is_premium) return false;
          if (!user.premium_until) return true; // Permanent premium
          
          const expiryDate = new Date(user.premium_until);
          return expiryDate > new Date();
        },

        // Actions
        login: async (credentials: LoginRequest) => {
          set({ isLoading: true, error: null });
          
          try {
            const response = await fetch('/api/v1/users/token/', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(credentials),
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              throw new Error(errorData.detail || 'Login failed');
            }

            const data: AuthResponse = await response.json();

            // Set tokens
            set({
              accessToken: data.access,
              refreshToken: data.refresh,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });

            // Fetch user profile
            const profileResponse = await fetch('/api/v1/auth/profile/', {
              headers: {
                'Authorization': `Bearer ${data.access}`,
              },
            });

            if (profileResponse.ok) {
              const user: User = await profileResponse.json();
              set({ user });
            }

          } catch (error) {
            const message = error instanceof Error ? error.message : 'Login failed';
            set({
              error: message,
              isLoading: false,
              isAuthenticated: false,
              accessToken: null,
              refreshToken: null,
              user: null,
            });
            throw error;
          }
        },

        logout: () => {
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            error: null,
          });
          
          // Clear localStorage
          localStorage.removeItem('auth-storage');
        },

        setTokens: (tokens) => {
          set({
            accessToken: tokens.access,
            refreshToken: tokens.refresh,
            isAuthenticated: true,
          });
        },

        setUser: (user) => {
          set({ 
            user,
            isAuthenticated: !!user,
          });
        },

        setError: (error) => {
          set({ error });
        },

        clearError: () => {
          set({ error: null });
        },

        refreshAccessToken: async () => {
          const { refreshToken } = get();
          
          if (!refreshToken) {
            throw new Error('No refresh token available');
          }

          if (isTokenExpired(refreshToken)) {
            // Refresh token expired, logout
            get().logout();
            throw new Error('Session expired. Please log in again.');
          }

          try {
            const response = await fetch('/api/v1/users/token/refresh/', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ refresh: refreshToken }),
            });

            if (!response.ok) {
              throw new Error('Token refresh failed');
            }

            const data = await response.json();
            
            set({
              accessToken: data.access,
              isAuthenticated: true,
            });

          } catch (error) {
            // Refresh failed, logout
            get().logout();
            throw error;
          }
        },
      }),
      {
        name: 'auth-storage',
        partialize: (state) => ({
          user: state.user,
          accessToken: state.accessToken,
          refreshToken: state.refreshToken,
          isAuthenticated: state.isAuthenticated,
        }),
      }
    ),
    { name: 'AuthStore' }
  )
);

// =============================================================================
// Hooks (Selectors)
// =============================================================================

export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useIsPremium = () => useAuthStore((state) => state.isPremium);
export const useTier = () => useAuthStore((state) => state.tier);
export const useAuthError = () => useAuthStore((state) => state.error);
