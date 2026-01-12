/**
 * React Query Configuration
 * 
 * Enterprise-grade query client with:
 * - Default stale/cache times
 * - Retry logic with exponential backoff
 * - Error handling
 * - Persistent query client (optional)
 * 
 * @module core/queryClient
 */

import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { toast } from '@/contexts/ToastContext';

// =============================================================================
// Error Handlers
// =============================================================================

/**
 * Handle query errors globally
 */
function handleQueryError(error: unknown) {
  const message = error instanceof Error ? error.message : 'An unexpected error occurred';
  
  // Don't show toast for network errors (handled by API client)
  if (message.includes('Network Error') || message.includes('timeout')) {
    return;
  }

  // Show error toast
  toast.error(message, {
    duration: 5000,
  });

  // Log to error tracking service (Sentry, LogRocket, etc.)
  if (process.env.NODE_ENV === 'production') {
    // TODO: Add error tracking
    console.error('[QueryError]', error);
  }
}

/**
 * Handle mutation errors globally
 */
function handleMutationError(error: unknown) {
  const message = error instanceof Error ? error.message : 'Operation failed';
  
  toast.error(message, {
    duration: 5000,
  });

  // Log to error tracking service
  if (process.env.NODE_ENV === 'production') {
    // TODO: Add error tracking
    console.error('[MutationError]', error);
  }
}

// =============================================================================
// Query Client
// =============================================================================

/**
 * Create and configure QueryClient
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time: 5 minutes (data is considered fresh for this duration)
      staleTime: 5 * 60 * 1000,
      
      // Cache time: 10 minutes (unused data stays in cache)
      gcTime: 10 * 60 * 1000,
      
      // Retry failed requests
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors (client errors)
        if (error instanceof Error && error.message.includes('40')) {
          return false;
        }
        
        // Retry up to 3 times for 5xx errors
        return failureCount < 3;
      },
      
      // Exponential backoff for retries
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      
      // Refetch on window focus (disabled by default, enable per-query)
      refetchOnWindowFocus: false,
      
      // Refetch on reconnect
      refetchOnReconnect: true,
      
      // Refetch on mount if data is stale
      refetchOnMount: true,
    },
    mutations: {
      // Retry mutations once
      retry: 1,
      
      // Retry delay for mutations
      retryDelay: 1000,
    },
  },
  
  // Global query cache with error handler
  queryCache: new QueryCache({
    onError: handleQueryError,
  }),
  
  // Global mutation cache with error handler
  mutationCache: new MutationCache({
    onError: handleMutationError,
  }),
});

// =============================================================================
// Query Keys Factory
// =============================================================================

/**
 * Centralized query keys for consistent caching
 * 
 * @example
 * ```ts
 * const { data } = useQuery({
 *   queryKey: queryKeys.stations.list({ province: 'Punjab' }),
 *   queryFn: () => fetchStations({ province: 'Punjab' })
 * });
 * ```
 */
export const queryKeys = {
  // Auth
  auth: {
    me: ['auth', 'me'] as const,
    refresh: ['auth', 'refresh'] as const,
  },
  
  // Stations
  stations: {
    all: ['stations'] as const,
    list: (filters?: Record<string, unknown>) => ['stations', 'list', filters] as const,
    detail: (id: string) => ['stations', 'detail', id] as const,
    readings: (id: string, params?: Record<string, unknown>) => 
      ['stations', id, 'readings', params] as const,
  },
  
  // GeoJSON
  geojson: {
    all: ['geojson'] as const,
    provinces: ['geojson', 'provinces'] as const,
    districts: (province?: string) => ['geojson', 'districts', province] as const,
  },
  
  // Exposure
  exposure: {
    all: ['exposure'] as const,
    district: (params?: Record<string, unknown>) => ['exposure', 'district', params] as const,
    population: (params?: Record<string, unknown>) => ['exposure', 'population', params] as const,
  },
  
  // GEE Satellite
  gee: {
    all: ['gee'] as const,
    dates: (pollutant: string) => ['gee', 'dates', pollutant] as const,
    data: (params: Record<string, unknown>) => ['gee', 'data', params] as const,
  },
  
  // Reports
  reports: {
    all: ['reports'] as const,
    list: (filters?: Record<string, unknown>) => ['reports', 'list', filters] as const,
    detail: (id: string) => ['reports', 'detail', id] as const,
  },
} as const;

// =============================================================================
// Query Invalidation Helpers
// =============================================================================

/**
 * Invalidate all queries
 */
export function invalidateAll() {
  return queryClient.invalidateQueries();
}

/**
 * Invalidate specific query keys
 */
export function invalidateQueries(queryKey: unknown[]) {
  return queryClient.invalidateQueries({ queryKey });
}

/**
 * Clear all query cache
 */
export function clearCache() {
  return queryClient.clear();
}

/**
 * Prefetch a query
 */
export function prefetchQuery<T>(
  queryKey: unknown[],
  queryFn: () => Promise<T>,
  options?: { staleTime?: number }
) {
  return queryClient.prefetchQuery({
    queryKey,
    queryFn,
    ...options,
  });
}

export default queryClient;
