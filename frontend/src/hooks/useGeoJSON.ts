/**
 * useGeoJSON Hook
 * 
 * Enterprise-grade TanStack Query wrapper for fetching GeoJSON data.
 * Provides strict typing with @types/geojson interfaces.
 * 
 * Features:
 * - Generic types for custom feature properties
 * - Automatic cache management
 * - Type-safe query keys
 * - Optimized for large GeoJSON payloads
 * 
 * @module hooks/useGeoJSON
 */

import { useQuery, UseQueryOptions, UseQueryResult } from '@tanstack/react-query';
import type { FeatureCollection, Feature, Geometry, GeoJsonProperties } from 'geojson';
import { get } from '@/lib/axios';
import { queryKeys, STALE_TIME, CACHE_TIME } from '@/lib/query-client';
import type { ApiError } from '@/lib/axios';

// =============================================================================
// Types
// =============================================================================

/**
 * Generic FeatureCollection type with custom properties
 * Uses standard @types/geojson for compatibility
 */
export type TypedFeatureCollection<
  P extends GeoJsonProperties = GeoJsonProperties,
  G extends Geometry = Geometry
> = FeatureCollection<G, P>;

/**
 * Generic Feature type with custom properties
 */
export type TypedFeature<
  P extends GeoJsonProperties = GeoJsonProperties,
  G extends Geometry = Geometry
> = Feature<G, P>;

/**
 * Options for useGeoJSON hook
 */
export interface UseGeoJSONOptions<
  TProperties extends GeoJsonProperties = GeoJsonProperties,
  TGeometry extends Geometry = Geometry
> extends Omit<
  UseQueryOptions<
    TypedFeatureCollection<TProperties, TGeometry>,
    ApiError,
    TypedFeatureCollection<TProperties, TGeometry>
  >,
  'queryKey' | 'queryFn'
> {
  /** URL parameters to append to the request */
  params?: Record<string, string | number | boolean | undefined>;
  /** Custom query key (defaults to endpoint-based key) */
  queryKey?: readonly unknown[];
}

/**
 * Return type for useGeoJSON hook
 */
export type UseGeoJSONResult<
  TProperties extends GeoJsonProperties = GeoJsonProperties,
  TGeometry extends Geometry = Geometry
> = UseQueryResult<TypedFeatureCollection<TProperties, TGeometry>, ApiError>;

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Fetch GeoJSON data with TanStack Query
 * 
 * @template TProperties - Type of feature properties (e.g., DistrictProperties)
 * @template TGeometry - Type of geometry (defaults to any Geometry)
 * 
 * @param endpoint - API endpoint (e.g., '/districts/geojson/')
 * @param options - Query options including params and TanStack Query options
 * @returns TanStack Query result with typed FeatureCollection
 * 
 * @example
 * ```tsx
 * // Basic usage
 * const { data, isLoading } = useGeoJSON('/districts/geojson/');
 * 
 * // With typed properties
 * interface DistrictProps { id: number; name: string; pm25_mean?: number; }
 * const { data } = useGeoJSON<DistrictProps>('/districts/geojson/');
 * 
 * // With parameters
 * const { data } = useGeoJSON<DistrictProps>('/districts/geojson/', {
 *   params: { province: 'Punjab' },
 * });
 * ```
 */
export function useGeoJSON<
  TProperties extends GeoJsonProperties = GeoJsonProperties,
  TGeometry extends Geometry = Geometry
>(
  endpoint: string,
  options: UseGeoJSONOptions<TProperties, TGeometry> = {}
): UseGeoJSONResult<TProperties, TGeometry> {
  const { params, queryKey, ...queryOptions } = options;

  // Filter out undefined params
  const filteredParams = params
    ? Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== undefined)
      )
    : undefined;

  // Build query key from endpoint and params
  const resolvedQueryKey = queryKey ?? [
    ...queryKeys.geojson.all,
    endpoint,
    filteredParams,
  ];

  return useQuery({
    queryKey: resolvedQueryKey,
    queryFn: async () => {
      const response = await get<TypedFeatureCollection<TProperties, TGeometry>>(
        endpoint,
        filteredParams
      );
      return response;
    },
    // GeoJSON-optimized defaults
    staleTime: STALE_TIME.GEOJSON,
    gcTime: CACHE_TIME.GEOJSON,
    // Disable refetch on window focus for large payloads
    refetchOnWindowFocus: false,
    // Merge with user options
    ...queryOptions,
  });
}

// =============================================================================
// Specialized Hooks
// =============================================================================

/**
 * Fetch provinces GeoJSON
 */
export function useProvincesGeoJSON<
  TProperties extends GeoJsonProperties = GeoJsonProperties
>(options?: Omit<UseGeoJSONOptions<TProperties>, 'params'>) {
  return useGeoJSON<TProperties>('/provinces/geojson/', {
    queryKey: queryKeys.geojson.provinces(),
    staleTime: STALE_TIME.STATIC,
    gcTime: CACHE_TIME.STATIC,
    ...options,
  });
}

/**
 * Fetch districts GeoJSON with optional province filter
 */
export function useDistrictsGeoJSON<
  TProperties extends GeoJsonProperties = GeoJsonProperties
>(
  province?: string,
  options?: Omit<UseGeoJSONOptions<TProperties>, 'params'>
) {
  return useGeoJSON<TProperties>('/districts/geojson/', {
    params: { province },
    queryKey: queryKeys.geojson.districts(province),
    staleTime: STALE_TIME.REFERENCE,
    gcTime: CACHE_TIME.REFERENCE,
    ...options,
  });
}

/**
 * Fetch stations GeoJSON with optional filters
 */
export function useStationsGeoJSON<
  TProperties extends GeoJsonProperties = GeoJsonProperties
>(
  params?: { district?: string; active?: boolean },
  options?: Omit<UseGeoJSONOptions<TProperties>, 'params'>
) {
  return useGeoJSON<TProperties>('/stations/geojson/', {
    params,
    queryKey: queryKeys.geojson.stations(params),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    ...options,
  });
}

export default useGeoJSON;
