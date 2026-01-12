/**
 * Legend & Reference Query Hooks
 * 
 * TanStack Query hooks for AQI legend, colors, and health messages.
 * These are static reference data that changes rarely.
 * 
 * @module hooks/queries/useLegend
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import api from '@/services/api';
import { STALE_TIME, CACHE_TIME } from '@/lib/query-client';
import type { ApiError } from '@/types/api';

// =============================================================================
// Types
// =============================================================================

/**
 * AQI Category configuration
 */
export interface AQICategory {
  range: [number, number];
  label: string;
  color: string;
  text_color: string;
  health_message: string;
  cautionary_statement: string;
}

/**
 * PM2.5 Breakpoint configuration
 */
export interface PM25Breakpoint {
  range: [number, number];
  aqi_range: [number, number];
  category: string;
  color: string;
}

/**
 * Full AQI Legend response
 */
export interface AQILegendResponse {
  aqi_categories: AQICategory[];
  pm25_breakpoints: PM25Breakpoint[];
  pollutant_info: Record<string, {
    name: string;
    unit: string;
    description: string;
  }>;
}

// =============================================================================
// Query Keys
// =============================================================================

/**
 * Query keys for legend domain
 */
export const legendKeys = {
  all: ['legend'] as const,
  aqi: () => [...legendKeys.all, 'aqi'] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch AQI legend with colors and health messages
 * 
 * Returns complete AQI category definitions, PM2.5 breakpoints,
 * and pollutant information. Cached for 24 hours as this rarely changes.
 * 
 * Endpoint: GET /api/v1/air-quality/legend/
 * 
 * @example
 * ```tsx
 * const { data: legend } = useAQILegend();
 * 
 * // Use for choropleth legend
 * legend?.aqi_categories.map(cat => (
 *   <div style={{ background: cat.color }}>{cat.label}</div>
 * ));
 * 
 * // Get health message for an AQI value
 * const category = legend?.aqi_categories.find(
 *   cat => aqi >= cat.range[0] && aqi <= cat.range[1]
 * );
 * console.log(category?.health_message);
 * ```
 */
export function useAQILegend(
  options?: Omit<UseQueryOptions<AQILegendResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<AQILegendResponse, ApiError>({
    queryKey: legendKeys.aqi(),
    queryFn: () => api.get<AQILegendResponse>('/legend/'),
    staleTime: STALE_TIME.STATIC, // 24 hours - rarely changes
    gcTime: CACHE_TIME.STATIC,
    refetchOnWindowFocus: false,
    ...options,
  });
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get AQI category for a given AQI value
 */
export function getAQICategory(
  aqi: number,
  categories: AQICategory[]
): AQICategory | undefined {
  return categories.find(
    cat => aqi >= cat.range[0] && aqi <= cat.range[1]
  );
}

/**
 * Get color for an AQI value
 */
export function getAQIColor(
  aqi: number,
  categories: AQICategory[]
): string {
  const category = getAQICategory(aqi, categories);
  return category?.color ?? '#999999';
}

/**
 * Get PM2.5 category for a concentration value
 */
export function getPM25Category(
  pm25: number,
  breakpoints: PM25Breakpoint[]
): PM25Breakpoint | undefined {
  return breakpoints.find(
    bp => pm25 >= bp.range[0] && pm25 <= bp.range[1]
  );
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch AQI legend for faster initial load
 * 
 * Call this during app initialization to have legend ready.
 */
export async function prefetchAQILegend(
  queryClient: ReturnType<typeof useQueryClient>
) {
  await queryClient.prefetchQuery({
    queryKey: legendKeys.aqi(),
    queryFn: () => api.get<AQILegendResponse>('/legend/'),
    staleTime: STALE_TIME.STATIC,
  });
}
