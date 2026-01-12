/**
 * GEE (Google Earth Engine) Query Hooks
 * 
 * TanStack Query hooks for Sentinel-5P satellite data via GEE.
 * Provides tile URLs, layer configurations, and available dates.
 * 
 * @module hooks/queries/useGEE
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import api from '@/services/api';
import { STALE_TIME, CACHE_TIME } from '@/lib/query-client';
import type { ApiError, GEETilesParams } from '@/types/api';

// =============================================================================
// Types
// =============================================================================

/**
 * Pollutant codes available in GEE
 */
export type GEEPollutant = 'NO2' | 'SO2' | 'CO' | 'O3' | 'HCHO' | 'CH4' | 'AER_AI';

/**
 * GEE Layer configuration from backend
 */
export interface GEELayerConfig {
  code: GEEPollutant;
  name: string;
  description: string;
  unit: string;
  collection: string;
  band: string;
  min_value: number;
  max_value: number;
  color_palette: string[];
}

/**
 * GEE Tile URL response
 */
export interface GEETileResponse {
  success: boolean;
  pollutant: string;
  date: string;
  composite_days: number;
  image_count: number;
  tiles: {
    url_template: string;
    attribution: string;
  };
  visualization?: {
    min: number;
    max: number;
    palette: string[];
  };
  layer?: {
    code: string;
    title: string;
    description: string;
    unit: string;
    band: string;
  };
}

/**
 * Available dates response
 */
export interface GEEDatesResponse {
  pollutant: string;
  available_dates: string[];
  latest_date: string;
  date_range: {
    start: string;
    end: string;
  };
}

// =============================================================================
// Query Keys
// =============================================================================

/**
 * Query keys for GEE domain
 */
export const geeKeys = {
  all: ['gee'] as const,
  layers: () => [...geeKeys.all, 'layers'] as const,
  tiles: (params: GEETilesParams) => [...geeKeys.all, 'tiles', params] as const,
  dates: (pollutant: string) => [...geeKeys.all, 'dates', pollutant] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch all available GEE layer configurations
 * 
 * Use this to populate a layer selector UI with all supported pollutants.
 * 
 * Endpoint: GET /api/v1/air-quality/gee/layers/
 * 
 * @example
 * ```tsx
 * const { data: layers } = useGEELayers();
 * // Returns: [{ code: 'NO2', name: 'Nitrogen Dioxide', ... }, ...]
 * ```
 */
export function useGEELayers(
  options?: Omit<UseQueryOptions<GEELayerConfig[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<GEELayerConfig[], ApiError>({
    queryKey: geeKeys.layers(),
    queryFn: () => api.get<GEELayerConfig[]>('/air-quality/gee/layers/'),
    staleTime: STALE_TIME.STATIC, // Layer configs rarely change
    gcTime: CACHE_TIME.STATIC,
    refetchOnWindowFocus: false,
    ...options,
  });
}

/**
 * Fetch GEE tile URL for a specific pollutant and date
 * 
 * Returns a MapLibre-compatible tile URL for rendering satellite data.
 * 
 * Endpoint: GET /api/v1/air-quality/gee/tiles/?pollutant=NO2&date=2025-01-15
 * 
 * @param pollutant - Pollutant code (NO2, SO2, CO, etc.)
 * @param date - Date string (YYYY-MM-DD)
 * @param options - Additional query options
 * 
 * @example
 * ```tsx
 * const { data: tileData } = useGEETiles('NO2', '2025-01-15');
 * // Use tileData.tile_url in MapLibre raster-tiles source
 * ```
 */
export function useGEETiles(
  pollutant: string,
  date: string,
  options?: Omit<UseQueryOptions<GEETileResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<GEETileResponse, ApiError>({
    queryKey: geeKeys.tiles({ pollutant, date }),
    queryFn: () => api.get<GEETileResponse>('/air-quality/gee/tiles/', { pollutant, date }),
    staleTime: STALE_TIME.REFERENCE, // Tiles can be cached for a while
    gcTime: CACHE_TIME.REFERENCE,
    enabled: !!pollutant && !!date,
    refetchOnWindowFocus: false,
    ...options,
  });
}

/**
 * Fetch available dates for a pollutant from GEE
 * 
 * Use this to populate a date picker with valid dates.
 * 
 * Endpoint: GET /api/v1/air-quality/gee/dates/?pollutant=NO2
 * 
 * @param pollutant - Pollutant code
 * @param options - Additional query options
 * 
 * @example
 * ```tsx
 * const { data: datesData } = useGEEDates('NO2');
 * // Use datesData.available_dates to show in date picker
 * // datesData.latest_date is the most recent available
 * ```
 */
export function useGEEDates(
  pollutant: string,
  options?: Omit<UseQueryOptions<GEEDatesResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<GEEDatesResponse, ApiError>({
    queryKey: geeKeys.dates(pollutant),
    queryFn: () => api.get<GEEDatesResponse>('/air-quality/gee/dates/', { pollutant }),
    staleTime: STALE_TIME.DYNAMIC, // Dates update daily
    gcTime: CACHE_TIME.DYNAMIC,
    enabled: !!pollutant,
    ...options,
  });
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch GEE layer configurations
 */
export async function prefetchGEELayers(
  queryClient: ReturnType<typeof useQueryClient>
) {
  await queryClient.prefetchQuery({
    queryKey: geeKeys.layers(),
    queryFn: () => api.get<GEELayerConfig[]>('/air-quality/gee/layers/'),
    staleTime: STALE_TIME.STATIC,
  });
}

/**
 * Prefetch tile URL for faster layer switching
 */
export async function prefetchGEETiles(
  queryClient: ReturnType<typeof useQueryClient>,
  pollutant: string,
  date: string
) {
  await queryClient.prefetchQuery({
    queryKey: geeKeys.tiles({ pollutant, date }),
    queryFn: () => api.get<GEETileResponse>('/air-quality/gee/tiles/', { pollutant, date }),
    staleTime: STALE_TIME.REFERENCE,
  });
}
