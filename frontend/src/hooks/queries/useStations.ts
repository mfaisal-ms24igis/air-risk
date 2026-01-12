/**
 * Stations Query Hooks
 * 
 * TanStack Query hooks for air quality station data.
 * Provides type-safe data fetching with automatic caching.
 * 
 * @module hooks/queries/useStations
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import type { FeatureCollection, Point } from 'geojson';
import api from '@/services/api';
import { STALE_TIME, CACHE_TIME } from '@/lib/query-client';
import type {
  AirQualityStation,
  StationProperties,
  PollutantReading,
  TimeSeriesPoint,
} from '@/types/models';
import type { ApiError, StationFilters, NearbyStationsParams, TimeSeriesParams } from '@/types/api';

// =============================================================================
// Types
// =============================================================================

/**
 * Station list response from API
 */
export type StationsResponse = AirQualityStation[];

/**
 * Station GeoJSON response
 */
export type StationsGeoJSON = FeatureCollection<Point, StationProperties>;

/**
 * Readings response
 */
export type ReadingsResponse = PollutantReading[];

/**
 * Time series response
 */
export type TimeSeriesResponse = TimeSeriesPoint[];

// =============================================================================
// Query Keys
// =============================================================================

/**
 * Query keys for stations domain
 */
export const stationKeys = {
  all: ['stations'] as const,
  lists: () => [...stationKeys.all, 'list'] as const,
  list: (filters?: StationFilters) => [...stationKeys.lists(), filters] as const,
  geojson: () => [...stationKeys.all, 'geojson'] as const,
  details: () => [...stationKeys.all, 'detail'] as const,
  detail: (id: number) => [...stationKeys.details(), id] as const,
  readings: (id: number) => [...stationKeys.detail(id), 'readings'] as const,
  timeseries: (id: number, params?: TimeSeriesParams) =>
    [...stationKeys.detail(id), 'timeseries', params] as const,
  nearby: (params: NearbyStationsParams) =>
    [...stationKeys.all, 'nearby', params] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch all stations list
 * 
 * @param filters - Optional filters (district, province, is_active)
 * @param options - Additional query options
 * @returns Query result with stations array
 * 
 * @example
 * ```tsx
 * const { data: stations, isLoading } = useStations({ is_active: true });
 * ```
 */
export function useStations(
  filters?: StationFilters,
  options?: Omit<UseQueryOptions<StationsResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<StationsResponse, ApiError>({
    queryKey: stationKeys.list(filters),
    queryFn: () => api.get<StationsResponse>('/stations/', filters),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    ...options,
  });
}

/**
 * Fetch stations as GeoJSON FeatureCollection
 * 
 * @param options - Additional query options
 * @returns Query result with GeoJSON FeatureCollection
 * 
 * @example
 * ```tsx
 * const { data: geojson } = useStationsGeoJSON();
 * // Use in MapLibre layer
 * ```
 */
export function useStationsGeoJSON(
  options?: Omit<UseQueryOptions<StationsGeoJSON, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<StationsGeoJSON, ApiError>({
    queryKey: stationKeys.geojson(),
    queryFn: () => api.get<StationsGeoJSON>('/air-quality/stations/geojson/', { has_data: 'false' }),
    staleTime: STALE_TIME.GEOJSON,
    gcTime: CACHE_TIME.GEOJSON,
    refetchOnWindowFocus: false,
    ...options,
  });
}

/**
 * Fetch a single station by ID
 * 
 * @param stationId - Station ID
 * @param options - Additional query options
 * @returns Query result with station details
 * 
 * @example
 * ```tsx
 * const { data: station } = useStation(123);
 * ```
 */
export function useStation(
  stationId: number,
  options?: Omit<UseQueryOptions<AirQualityStation, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<AirQualityStation, ApiError>({
    queryKey: stationKeys.detail(stationId),
    queryFn: () => api.get<AirQualityStation>(`/stations/${stationId}/`),
    staleTime: STALE_TIME.REFERENCE,
    gcTime: CACHE_TIME.REFERENCE,
    enabled: !!stationId,
    ...options,
  });
}

/**
 * Fetch readings for a station
 * 
 * @param stationId - Station ID
 * @param days - Number of days of history (default 7)
 * @param options - Additional query options
 * @returns Query result with readings array
 * 
 * @example
 * ```tsx
 * const { data: readings } = useStationReadings(123, 30);
 * ```
 */
export function useStationReadings(
  stationId: number,
  days: number = 7,
  options?: Omit<UseQueryOptions<ReadingsResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ReadingsResponse, ApiError>({
    queryKey: stationKeys.readings(stationId),
    queryFn: () =>
      api.get<ReadingsResponse>(`/stations/${stationId}/readings/`, { days }),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    enabled: !!stationId,
    ...options,
  });
}

/**
 * Fetch time series data for a station
 * 
 * @param stationId - Station ID
 * @param params - Time series parameters (parameter, interval, days)
 * @param options - Additional query options
 * @returns Query result with time series data
 * 
 * @example
 * ```tsx
 * const { data: timeseries } = useStationTimeSeries(123, {
 *   parameter: 'PM25',
 *   interval: 'daily',
 *   days: 30,
 * });
 * ```
 */
export function useStationTimeSeries(
  stationId: number,
  params: TimeSeriesParams,
  options?: Omit<UseQueryOptions<TimeSeriesResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<TimeSeriesResponse, ApiError>({
    queryKey: stationKeys.timeseries(stationId, params),
    queryFn: () =>
      api.get<TimeSeriesResponse>(`/stations/${stationId}/timeseries/`, params),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    enabled: !!stationId && !!params.parameter,
    ...options,
  });
}

/**
 * Fetch stations near a geographic point
 * 
 * @param params - Location and radius parameters
 * @param options - Additional query options
 * @returns Query result with nearby stations
 * 
 * @example
 * ```tsx
 * const { data: nearby } = useNearbyStations({
 *   lat: 31.5204,
 *   lon: 74.3587,
 *   radius: 25,
 * });
 * ```
 */
export function useNearbyStations(
  params: NearbyStationsParams,
  options?: Omit<UseQueryOptions<StationsResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<StationsResponse, ApiError>({
    queryKey: stationKeys.nearby(params),
    queryFn: () => api.get<StationsResponse>('/stations/nearby/', params),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    enabled: !!params.lat && !!params.lon,
    ...options,
  });
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch stations list for faster navigation
 * 
 * @example
 * ```tsx
 * const queryClient = useQueryClient();
 * await prefetchStations(queryClient);
 * ```
 */
export async function prefetchStations(
  queryClient: ReturnType<typeof useQueryClient>,
  filters?: StationFilters
) {
  await queryClient.prefetchQuery({
    queryKey: stationKeys.list(filters),
    queryFn: () => api.get<StationsResponse>('/stations/', filters),
    staleTime: STALE_TIME.DYNAMIC,
  });
}

/**
 * Prefetch station detail
 */
export async function prefetchStation(
  queryClient: ReturnType<typeof useQueryClient>,
  stationId: number
) {
  await queryClient.prefetchQuery({
    queryKey: stationKeys.detail(stationId),
    queryFn: () => api.get<AirQualityStation>(`/stations/${stationId}/`),
    staleTime: STALE_TIME.REFERENCE,
  });
}
