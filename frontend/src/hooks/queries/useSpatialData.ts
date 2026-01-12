/**
 * React Query Hooks for Spatial APIs
 * 
 * Hooks for the new tiered spatial endpoints with proper caching
 * 
 * @module hooks/queries/useSpatialData
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-client';
import * as spatialApi from '@/services/spatialApi';

// =============================================================================
// District Hooks
// =============================================================================

/**
 * Get all districts with tier-appropriate data
 */
export function useDistricts(params?: { simplified?: boolean }) {
  return useQuery({
    queryKey: ['districts', 'list', params],
    queryFn: () => spatialApi.getDistricts(params),
    staleTime: 10 * 60 * 1000, // 10 minutes - districts don't change often
  });
}

/**
 * Get single district detail
 */
export function useDistrictDetail(districtId: number | null) {
  return useQuery({
    queryKey: ['districts', 'detail', districtId],
    queryFn: () => spatialApi.getDistrictDetail(districtId!),
    enabled: districtId !== null,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Get district raster tiles (PREMIUM ONLY)
 */
export function useDistrictTiles(
  districtId: number | null,
  params: { pollutant: string; date?: string }
) {
  return useQuery({
    queryKey: ['districts', districtId, 'tiles', params],
    queryFn: () => spatialApi.getDistrictTiles(districtId!, params),
    enabled: districtId !== null,
    staleTime: 60 * 60 * 1000, // 1 hour - tiles are cached
  });
}

// =============================================================================
// Station Hooks
// =============================================================================

/**
 * Find stations near a location
 */
export function useStationsNearby(
  params: {
    lat: number;
    lng: number;
    radius?: number;
    limit?: number;
  } | null
) {
  return useQuery({
    queryKey: ['stations', 'nearby', params],
    queryFn: () => spatialApi.getStationsNearby(params!),
    enabled: params !== null && params.lat !== 0 && params.lng !== 0,
    staleTime: 2 * 60 * 1000, // 2 minutes - readings change frequently
  });
}

/**
 * Get latest readings from all stations
 */
export function useLatestStationReadings(params?: {
  parameter?: string;
  active_only?: boolean;
}) {
  return useQuery({
    queryKey: ['stations', 'latest', params],
    queryFn: () => spatialApi.getLatestStationReadings(params),
    staleTime: 1 * 60 * 1000, // 1 minute - latest readings
    refetchInterval: 5 * 60 * 1000, // Auto-refetch every 5 minutes
  });
}

/**
 * Get station detail with recent readings
 */
export function useStationDetail(stationId: number | null) {
  return useQuery({
    queryKey: ['stations', 'detail', stationId],
    queryFn: () => spatialApi.getStationDetail(stationId!),
    enabled: stationId !== null,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Get station timeseries for charts
 */
export function useStationTimeseries(
  stationId: number | null,
  params?: {
    parameter?: string;
    days?: number;
    interval?: 'hourly' | 'daily';
  }
) {
  return useQuery({
    queryKey: ['stations', stationId, 'timeseries', params],
    queryFn: () => spatialApi.getStationTimeseries(stationId!, params),
    enabled: stationId !== null,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// =============================================================================
// GEE Hooks
// =============================================================================

/**
 * Get available dates for a pollutant in GEE
 */
export function useGEEDatesNew(pollutant: string) {
  return useQuery({
    queryKey: ['gee', 'dates', pollutant],
    queryFn: () => spatialApi.getGEEDates(pollutant),
    staleTime: 60 * 60 * 1000, // 1 hour - available dates don't change often
  });
}

/**
 * Get GEE tile URL for rendering
 */
export function useGEETiles(params: { pollutant: string; date: string } | null) {
  return useQuery({
    queryKey: ['gee', 'tiles', params],
    queryFn: () => spatialApi.getGEETiles(params!),
    enabled: params !== null && params.pollutant !== '' && params.date !== '',
    staleTime: 60 * 60 * 1000, // 1 hour - tiles are cached
  });
}

// =============================================================================
// Exposure Hooks
// =============================================================================

/**
 * Get district exposure data
 * Note: Exposure API may not always be available - query is optional
 */
export function useDistrictExposure(params?: {
  date?: string;
  pollutant?: string;
  province?: string;
  enabled?: boolean;
}) {
  const { enabled = false, ...queryParams } = params || {};
  return useQuery({
    queryKey: ['exposure', 'districts', queryParams],
    queryFn: () => spatialApi.getDistrictExposure(queryParams),
    staleTime: 10 * 60 * 1000, // 10 minutes
    enabled: enabled, // Only run if explicitly enabled
    retry: false, // Don't retry on 404
  });
}

// =============================================================================
// Export all
// =============================================================================

export default {
  useDistricts,
  useDistrictDetail,
  useDistrictTiles,
  useStationsNearby,
  useLatestStationReadings,
  useStationDetail,
  useStationTimeseries,
  useGEEDatesNew,
  useGEETiles,
  useDistrictExposure,
};
