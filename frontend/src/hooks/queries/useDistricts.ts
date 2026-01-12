/**
 * Districts Query Hooks
 * 
 * TanStack Query hooks for district geographic data.
 * 
 * @module hooks/queries/useDistricts
 */

import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import type { FeatureCollection, Polygon, MultiPolygon } from 'geojson';
import api from '@/services/api';
import { STALE_TIME, CACHE_TIME } from '@/lib/query-client';
import type { District, DistrictProperties } from '@/types/models';
import type { ApiError, DistrictFilters } from '@/types/api';

// =============================================================================
// Types
// =============================================================================

export type DistrictsResponse = District[];
export type DistrictsGeoJSON = FeatureCollection<Polygon | MultiPolygon, DistrictProperties>;

// =============================================================================
// Query Keys
// =============================================================================

export const districtKeys = {
  all: ['districts'] as const,
  lists: () => [...districtKeys.all, 'list'] as const,
  list: (filters?: DistrictFilters) => [...districtKeys.lists(), filters] as const,
  geojson: (province?: string) => [...districtKeys.all, 'geojson', province] as const,
  details: () => [...districtKeys.all, 'detail'] as const,
  detail: (id: number) => [...districtKeys.details(), id] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch districts list
 */
export function useDistricts(
  filters?: DistrictFilters,
  options?: Omit<UseQueryOptions<DistrictsResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<DistrictsResponse, ApiError>({
    queryKey: districtKeys.list(filters),
    queryFn: () => api.get<DistrictsResponse>('/districts/', filters),
    staleTime: STALE_TIME.REFERENCE,
    gcTime: CACHE_TIME.REFERENCE,
    ...options,
  });
}

/**
 * Fetch districts as GeoJSON
 * 
 * @param province - Optional province filter
 */
export function useDistrictsGeoJSON(
  province?: string,
  options?: Omit<UseQueryOptions<DistrictsGeoJSON, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<DistrictsGeoJSON, ApiError>({
    queryKey: districtKeys.geojson(province),
    queryFn: () =>
      api.get<DistrictsGeoJSON>('/districts/geojson/', province ? { province } : undefined),
    staleTime: STALE_TIME.STATIC,
    gcTime: CACHE_TIME.STATIC,
    refetchOnWindowFocus: false,
    ...options,
  });
}

/**
 * Fetch single district
 */
export function useDistrict(
  districtId: number,
  options?: Omit<UseQueryOptions<District, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<District, ApiError>({
    queryKey: districtKeys.detail(districtId),
    queryFn: () => api.get<District>(`/districts/${districtId}/`),
    staleTime: STALE_TIME.STATIC,
    gcTime: CACHE_TIME.STATIC,
    enabled: !!districtId,
    ...options,
  });
}
