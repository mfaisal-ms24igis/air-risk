/**
 * TanStack Query Client Configuration
 * 
 * Enterprise-grade query client with:
 * - Optimized stale/cache times for GIS data
 * - Global error handling with toast notifications
 * - Retry logic with exponential backoff
 * - Structural sharing for performance
 * - Centralized query keys factory
 * 
 * @module lib/query-client
 */

import { QueryClient, QueryClientConfig, QueryCache, MutationCache } from '@tanstack/react-query';
import type { ApiError } from './axios';

// =============================================================================
// Cache Time Constants
// =============================================================================

/**
 * Time constants in milliseconds
 * Calibrated for GIS data that changes infrequently
 */
export const CACHE_TIME = {
  /** Data that rarely changes (boundaries, static layers) */
  STATIC: 1000 * 60 * 60 * 24, // 24 hours
  
  /** Reference data (provinces, districts) */
  REFERENCE: 1000 * 60 * 60, // 1 hour
  
  /** Data that updates periodically (air quality readings) */
  DYNAMIC: 1000 * 60 * 5, // 5 minutes
  
  /** Near real-time data (latest readings) */
  REALTIME: 1000 * 60, // 1 minute
  
  /** GeoJSON geometries (large, stable) */
  GEOJSON: 1000 * 60 * 30, // 30 minutes
} as const;

export const STALE_TIME = {
  /** Data considered fresh immediately after fetch */
  STATIC: 1000 * 60 * 60, // 1 hour
  
  /** Reference data stale time */
  REFERENCE: 1000 * 60 * 15, // 15 minutes
  
  /** Dynamic data stale time */
  DYNAMIC: 1000 * 60 * 2, // 2 minutes
  
  /** Real-time data stale time */
  REALTIME: 1000 * 30, // 30 seconds
  
  /** GeoJSON stale time */
  GEOJSON: 1000 * 60 * 10, // 10 minutes
} as const;

// =============================================================================
// Retry Logic
// =============================================================================

/**
 * Determines if a failed request should be retried
 * 
 * @param failureCount - Number of previous failures
 * @param error - The error that caused the failure
 * @returns Whether to retry the request
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  // Max 3 retries
  if (failureCount >= 3) return false;

  // Don't retry client errors (4xx)
  const apiError = error as ApiError;
  if (apiError.statusCode && apiError.statusCode >= 400 && apiError.statusCode < 500) {
    return false;
  }

  // Retry network errors and server errors (5xx)
  return true;
}

/**
 * Calculate retry delay with exponential backoff
 * 
 * @param attemptIndex - The retry attempt number (0-indexed)
 * @returns Delay in milliseconds
 */
function getRetryDelay(attemptIndex: number): number {
  // Exponential backoff: 1s, 2s, 4s
  const baseDelay = 1000;
  const maxDelay = 10000;
  const delay = Math.min(baseDelay * Math.pow(2, attemptIndex), maxDelay);
  
  // Add jitter to prevent thundering herd
  const jitter = delay * 0.1 * Math.random();
  return delay + jitter;
}

// =============================================================================
// Global Error Handler
// =============================================================================

/**
 * Global error handler for queries
 */
function onQueryError(error: unknown): void {
  const apiError = error as ApiError;
  
  if (import.meta.env.DEV) {
    console.error('[Query Error]', apiError);
  }

  // Skip toast for network errors (handled by API client)
  const message = apiError.message || 'An unexpected error occurred';
  if (message.includes('Network Error') || message.includes('timeout')) {
    return;
  }

  // Note: Toast context is not available here (outside React tree)
  // Individual queries should handle their own error toasts
}

/**
 * Global error handler for all mutations
 */
function onMutationError(error: unknown): void {
  const apiError = error as ApiError;
  
  if (import.meta.env.DEV) {
    console.error('[Mutation Error]', apiError);
  }

  // Note: Toast context is not available here (outside React tree)
  // Individual mutations should handle their own error toasts
}

// =============================================================================
// Query Client Configuration
// =============================================================================

const queryClientConfig: QueryClientConfig = {
  defaultOptions: {
    queries: {
      // Default cache configuration
      staleTime: STALE_TIME.REFERENCE,
      gcTime: CACHE_TIME.REFERENCE, // gcTime replaces cacheTime in v5
      
      // Retry configuration
      retry: shouldRetry,
      retryDelay: getRetryDelay,
      
      // Refetch behavior
      refetchOnWindowFocus: false, // Disable for GIS apps (large data)
      refetchOnReconnect: true,
      refetchOnMount: true,
      
      // Network mode
      networkMode: 'offlineFirst', // Use cache when offline
      
      // Structural sharing for performance
      structuralSharing: true,
    },
    mutations: {
      // Retry configuration for mutations
      retry: 1,
      retryDelay: 1000,
      
      // Network mode
      networkMode: 'online',
    },
  },
  
  // Global query cache with error handler
  queryCache: new QueryCache({
    onError: onQueryError,
  }),
  
  // Global mutation cache with error handler
  mutationCache: new MutationCache({
    onError: onMutationError,
  }),
};

// =============================================================================
// Query Client Instance
// =============================================================================

/**
 * Singleton QueryClient instance
 * 
 * Use this throughout the app for consistent caching behavior
 */
export const queryClient = new QueryClient(queryClientConfig);

// =============================================================================
// Query Key Factories
// =============================================================================

/**
 * Type-safe query key factory
 * 
 * Ensures consistent query keys across the application
 * Following TanStack Query best practices
 */
export const queryKeys = {
  // GeoJSON endpoints
  geojson: {
    all: ['geojson'] as const,
    provinces: () => [...queryKeys.geojson.all, 'provinces'] as const,
    districts: (province?: string) => 
      [...queryKeys.geojson.all, 'districts', { province }] as const,
    stations: (params?: { district?: string; active?: boolean }) =>
      [...queryKeys.geojson.all, 'stations', params] as const,
  },
  
  // Administrative boundaries
  boundaries: {
    all: ['boundaries'] as const,
    province: (id: number) => [...queryKeys.boundaries.all, 'province', id] as const,
    district: (id: number) => [...queryKeys.boundaries.all, 'district', id] as const,
  },
  
  // Air quality data
  airQuality: {
    all: ['air-quality'] as const,
    latest: (stationId?: number) => 
      [...queryKeys.airQuality.all, 'latest', { stationId }] as const,
    timeseries: (stationId: number, params?: { days?: number; parameter?: string }) =>
      [...queryKeys.airQuality.all, 'timeseries', stationId, params] as const,
  },
  
  // GEE tiles
  gee: {
    all: ['gee'] as const,
    layers: () => [...queryKeys.gee.all, 'layers'] as const,
    tiles: (layer: string, date: string) =>
      [...queryKeys.gee.all, 'tiles', layer, date] as const,
    dates: (layer: string) =>
      [...queryKeys.gee.all, 'dates', layer] as const,
  },
  
  // Reference data
  reference: {
    all: ['reference'] as const,
    legend: () => [...queryKeys.reference.all, 'legend'] as const,
  },
} as const;

export default queryClient;
