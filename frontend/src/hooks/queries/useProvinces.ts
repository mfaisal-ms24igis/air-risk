/**
 * Provinces Query Hooks
 * 
 * TanStack Query hooks for province geographic data.
 * 
 * @module hooks/queries/useProvinces
 */

import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import type { FeatureCollection, Polygon, MultiPolygon } from 'geojson';
import api from '@/services/api';
import { STALE_TIME, CACHE_TIME } from '@/lib/query-client';
import type { Province, ProvinceProperties } from '@/types/models';
import type { ApiError } from '@/types/api';

// =============================================================================
// Types
// =============================================================================

export type ProvincesResponse = Province[];
export type ProvincesGeoJSON = FeatureCollection<Polygon | MultiPolygon, ProvinceProperties>;

// =============================================================================
// Query Keys
// =============================================================================

export const provinceKeys = {
  all: ['provinces'] as const,
  list: () => [...provinceKeys.all, 'list'] as const,
  geojson: () => [...provinceKeys.all, 'geojson'] as const,
  details: () => [...provinceKeys.all, 'detail'] as const,
  detail: (id: number) => [...provinceKeys.details(), id] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch provinces list
 */
export function useProvinces(
  options?: Omit<UseQueryOptions<ProvincesResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ProvincesResponse, ApiError>({
    queryKey: provinceKeys.list(),
    queryFn: () => api.get<ProvincesResponse>('/provinces/'),
    staleTime: STALE_TIME.STATIC,
    gcTime: CACHE_TIME.STATIC,
    ...options,
  });
}

/**
 * Fetch provinces as GeoJSON
 */
export function useProvincesGeoJSON(
  options?: Omit<UseQueryOptions<ProvincesGeoJSON, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ProvincesGeoJSON, ApiError>({
    queryKey: provinceKeys.geojson(),
    queryFn: () => api.get<ProvincesGeoJSON>('/air-quality/provinces/geojson/'),
    staleTime: STALE_TIME.STATIC,
    gcTime: CACHE_TIME.STATIC,
    refetchOnWindowFocus: false,
    ...options,
  });
}

/**
 * Fetch single province
 */
export function useProvince(
  provinceId: number,
  options?: Omit<UseQueryOptions<Province, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<Province, ApiError>({
    queryKey: provinceKeys.detail(provinceId),
    queryFn: () => api.get<Province>(`/provinces/${provinceId}/`),
    staleTime: STALE_TIME.STATIC,
    gcTime: CACHE_TIME.STATIC,
    enabled: !!provinceId,
    ...options,
  });
}
