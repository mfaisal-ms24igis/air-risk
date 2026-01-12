/**
 * Exposure Query Hooks
 * 
 * TanStack Query hooks for exposure analytics API.
 * These endpoints have air quality data (PM2.5, AQI, exposure metrics).
 * 
 * @module hooks/queries/useExposure
 */

import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import exposureApi from '@/services/exposureApi';
import { STALE_TIME, CACHE_TIME } from '@/lib/query-client';
import type { ApiError } from '@/types/api';
import type {
  DistrictExposure,
  DistrictExposureGeoJSON,
  ProvinceExposure,
  NationalExposure,
  DashboardData,
  ExposureTrends,
  Hotspot,
} from '@/types/exposure';

// =============================================================================
// Query Keys
// =============================================================================

export const exposureKeys = {
  all: ['exposure'] as const,
  
  // Dashboard
  dashboard: () => [...exposureKeys.all, 'dashboard'] as const,
  
  // Districts
  districts: () => [...exposureKeys.all, 'districts'] as const,
  districtList: (params?: DistrictExposureParams) => 
    [...exposureKeys.districts(), 'list', params] as const,
  districtDetail: (id: number) => 
    [...exposureKeys.districts(), 'detail', id] as const,
  districtGeoJSON: (params?: DistrictGeoJSONParams) => 
    [...exposureKeys.districts(), 'geojson', params] as const,
  
  // Provinces
  provinces: () => [...exposureKeys.all, 'provinces'] as const,
  provinceList: () => [...exposureKeys.provinces(), 'list'] as const,
  provinceDetail: (id: number) => [...exposureKeys.provinces(), 'detail', id] as const,
  
  // National
  national: () => [...exposureKeys.all, 'national'] as const,
  nationalList: () => [...exposureKeys.national(), 'list'] as const,
  
  // Trends
  trends: (params: TrendParams) => [...exposureKeys.all, 'trends', params] as const,
  
  // Hotspots
  hotspots: () => [...exposureKeys.all, 'hotspots'] as const,
};

// =============================================================================
// Types
// =============================================================================

export interface DistrictExposureParams {
  province?: string;
  date?: string;
}

export interface DistrictGeoJSONParams {
  province?: string;
  date?: string;
}

export interface TrendParams {
  scope?: 'national' | 'province' | 'district';
  scope_id?: number;
  days?: number;
}

// =============================================================================
// Dashboard Hook
// =============================================================================

/**
 * Fetch dashboard data with national summary, province rankings, worst districts
 * 
 * Endpoint: GET /api/v1/exposure/dashboard/
 */
export function useDashboard(
  options?: Omit<UseQueryOptions<DashboardData, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<DashboardData, ApiError>({
    queryKey: exposureKeys.dashboard(),
    queryFn: () => exposureApi.get<DashboardData>('/dashboard/'),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    ...options,
  });
}

// =============================================================================
// District Exposure Hooks
// =============================================================================

/**
 * Fetch district exposure list with air quality data
 * 
 * Endpoint: GET /api/v1/exposure/districts/
 */
export function useDistrictExposures(
  params?: DistrictExposureParams,
  options?: Omit<UseQueryOptions<DistrictExposure[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<DistrictExposure[], ApiError>({
    queryKey: exposureKeys.districtList(params),
    queryFn: () => exposureApi.get<DistrictExposure[]>('/districts/', params as Record<string, unknown>),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    ...options,
  });
}

/**
 * Fetch single district exposure detail
 * 
 * Endpoint: GET /api/v1/exposure/districts/{id}/
 */
export function useDistrictExposure(
  districtId: number,
  options?: Omit<UseQueryOptions<DistrictExposure, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<DistrictExposure, ApiError>({
    queryKey: exposureKeys.districtDetail(districtId),
    queryFn: () => exposureApi.get<DistrictExposure>(`/districts/${districtId}/`),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    enabled: !!districtId,
    ...options,
  });
}

/**
 * Fetch district exposure as GeoJSON with air quality data
 * 
 * This is the KEY endpoint for map visualization with PM2.5/AQI data!
 * 
 * Endpoint: GET /api/v1/exposure/geojson/districts/
 * 
 * @example
 * ```tsx
 * const { data } = useDistrictExposureGeoJSON({ province: 'Punjab' });
 * // data.features[0].properties.mean_pm25
 * // data.features[0].properties.aqi_color
 * ```
 */
export function useDistrictExposureGeoJSON(
  params?: DistrictGeoJSONParams,
  options?: Omit<UseQueryOptions<DistrictExposureGeoJSON, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<DistrictExposureGeoJSON, ApiError>({
    queryKey: exposureKeys.districtGeoJSON(params),
    queryFn: () => exposureApi.get<DistrictExposureGeoJSON>('/geojson/districts/', params as Record<string, unknown>),
    staleTime: STALE_TIME.GEOJSON,
    gcTime: CACHE_TIME.GEOJSON,
    refetchOnWindowFocus: false,
    ...options,
  });
}

// =============================================================================
// Province Exposure Hooks
// =============================================================================

/**
 * Fetch province exposure summaries
 * 
 * Endpoint: GET /api/v1/exposure/provinces/
 */
export function useProvinceExposures(
  options?: Omit<UseQueryOptions<ProvinceExposure[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ProvinceExposure[], ApiError>({
    queryKey: exposureKeys.provinceList(),
    queryFn: () => exposureApi.get<ProvinceExposure[]>('/provinces/'),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    ...options,
  });
}

/**
 * Fetch single province exposure detail
 */
export function useProvinceExposure(
  provinceId: number,
  options?: Omit<UseQueryOptions<ProvinceExposure, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ProvinceExposure, ApiError>({
    queryKey: exposureKeys.provinceDetail(provinceId),
    queryFn: () => exposureApi.get<ProvinceExposure>(`/provinces/${provinceId}/`),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    enabled: !!provinceId,
    ...options,
  });
}

// =============================================================================
// National Exposure Hook
// =============================================================================

/**
 * Fetch national exposure summary
 * 
 * Endpoint: GET /api/v1/exposure/national/
 */
export function useNationalExposure(
  options?: Omit<UseQueryOptions<NationalExposure[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<NationalExposure[], ApiError>({
    queryKey: exposureKeys.nationalList(),
    queryFn: () => exposureApi.get<NationalExposure[]>('/national/'),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    ...options,
  });
}

// =============================================================================
// Trends Hook
// =============================================================================

/**
 * Fetch exposure trends over time
 * 
 * Endpoint: GET /api/v1/exposure/trends/
 */
export function useExposureTrends(
  params: TrendParams,
  options?: Omit<UseQueryOptions<ExposureTrends, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ExposureTrends, ApiError>({
    queryKey: exposureKeys.trends(params),
    queryFn: () => exposureApi.get<ExposureTrends>('/trends/', params as Record<string, unknown>),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    ...options,
  });
}

// =============================================================================
// Hotspots Hook
// =============================================================================

/**
 * Fetch air quality hotspots (worst areas)
 * 
 * Endpoint: GET /api/v1/exposure/hotspots/
 */
export function useHotspots(
  options?: Omit<UseQueryOptions<Hotspot[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<Hotspot[], ApiError>({
    queryKey: exposureKeys.hotspots(),
    queryFn: () => exposureApi.get<Hotspot[]>('/hotspots/'),
    staleTime: STALE_TIME.DYNAMIC,
    gcTime: CACHE_TIME.DYNAMIC,
    ...options,
  });
}
