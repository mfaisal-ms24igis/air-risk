/**
 * WMS Layers Query Hooks
 * 
 * TanStack Query hooks for Sentinel-5P data via GeoServer WMS.
 * Alternative to GEE for on-premise deployments.
 * 
 * @module hooks/queries/useWMS
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
 * WMS Layer configuration from backend
 */
export interface WMSLayerConfig {
  id: number;
  pollutant: string;
  date: string;
  workspace: string;
  layer_name: string;
  store_name: string;
  wms_url: string;
  has_raw: boolean;
  has_corrected: boolean;
  stats?: {
    min: number;
    max: number;
    mean: number;
    std_dev: number;
  };
}

/**
 * WMS Time series response
 */
export interface WMSTimeSeriesResponse {
  pollutant: string;
  available_dates: string[];
  layers: WMSLayerConfig[];
}

/**
 * Filter params for WMS layers
 */
export interface WMSLayersParams {
  pollutant?: string;
  date?: string;
}

// =============================================================================
// Query Keys
// =============================================================================

/**
 * Query keys for WMS domain
 */
export const wmsKeys = {
  all: ['wms'] as const,
  layers: (params?: WMSLayersParams) => [...wmsKeys.all, 'layers', params] as const,
  timeseries: (pollutant?: string) => [...wmsKeys.all, 'timeseries', pollutant] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch WMS layer configurations
 * 
 * Returns available Sentinel-5P raster layers from GeoServer.
 * 
 * Endpoint: GET /api/v1/air-quality/wms/layers/
 * Endpoint: GET /api/v1/air-quality/wms/layers/?pollutant=NO2&date=2025-12-01
 * 
 * @param params - Optional filter by pollutant and/or date
 * @param options - Additional query options
 * 
 * @example
 * ```tsx
 * // Get all layers
 * const { data: layers } = useWMSLayers();
 * 
 * // Filter by pollutant
 * const { data: no2Layers } = useWMSLayers({ pollutant: 'NO2' });
 * ```
 */
export function useWMSLayers(
  params?: WMSLayersParams,
  options?: Omit<UseQueryOptions<WMSLayerConfig[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<WMSLayerConfig[], ApiError>({
    queryKey: wmsKeys.layers(params),
    queryFn: () => api.get<WMSLayerConfig[]>('/wms/layers/', params as Record<string, unknown>),
    staleTime: STALE_TIME.REFERENCE,
    gcTime: CACHE_TIME.REFERENCE,
    refetchOnWindowFocus: false,
    ...options,
  });
}

/**
 * Fetch WMS time series for a pollutant
 * 
 * Returns all available time steps for a pollutant.
 * 
 * Endpoint: GET /api/v1/air-quality/wms/timeseries/?pollutant=NO2
 * 
 * @param pollutant - Pollutant code
 * @param options - Additional query options
 * 
 * @example
 * ```tsx
 * const { data: timeseries } = useWMSTimeSeries('NO2');
 * // Use timeseries.available_dates for time slider
 * ```
 */
export function useWMSTimeSeries(
  pollutant?: string,
  options?: Omit<UseQueryOptions<WMSTimeSeriesResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<WMSTimeSeriesResponse, ApiError>({
    queryKey: wmsKeys.timeseries(pollutant),
    queryFn: () => api.get<WMSTimeSeriesResponse>('/wms/timeseries/', { pollutant }),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    enabled: !!pollutant,
    ...options,
  });
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch WMS layers for a pollutant
 */
export async function prefetchWMSLayers(
  queryClient: ReturnType<typeof useQueryClient>,
  params?: WMSLayersParams
) {
  await queryClient.prefetchQuery({
    queryKey: wmsKeys.layers(params),
    queryFn: () => api.get<WMSLayerConfig[]>('/wms/layers/', params as Record<string, unknown>),
    staleTime: STALE_TIME.REFERENCE,
  });
}
