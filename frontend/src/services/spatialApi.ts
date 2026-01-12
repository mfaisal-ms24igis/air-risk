/**
 * Tiered Air Quality API Service
 * 
 * Uses the new backend spatial endpoints with tier-based access control:
 * - /api/v1/air-quality/spatial/districts/ (tiered)
 * - /api/v1/air-quality/spatial/districts/{id}/ (tiered)
 * - /api/v1/air-quality/spatial/districts/{id}/tiles/ (premium only)
 * - /api/v1/air-quality/spatial/stations/nearby/ (tiered)
 * 
 * @module services/spatialApi
 */

import { apiClient } from '@/core/api/client';

// =============================================================================
// Types
// =============================================================================

export interface DistrictListItem {
  id: number;
  name: string;
  geometry?: any; // GeoJSON geometry
  aqi?: number;
  aqi_category?: string;
  // Premium fields
  pollutants?: {
    PM25?: number;
    PM10?: number;
    NO2?: number;
    SO2?: number;
    CO?: number;
    O3?: number;
  };
  station_count?: number;
}

export interface DistrictDetail extends DistrictListItem {
  province?: string;
  bounds?: [number, number, number, number]; // [minLng, minLat, maxLng, maxLat]
  stations?: StationItem[];
  trend?: {
    direction: 'improving' | 'worsening' | 'stable';
    change_percent?: number;
  };
}

export interface StationItem {
  id: number;
  name: string;
  location: {
    type: 'Point';
    coordinates: [number, number]; // [lng, lat]
  };
  latest_reading?: {
    PM25?: number;
    PM10?: number;
    NO2?: number;
    aqi?: number;
    timestamp?: string;
  };
  is_active: boolean;
}

export interface TileInfo {
  pollutant: string;
  date: string;
  url: string;
  bounds: [number, number, number, number];
  expires_at: string;
}

// =============================================================================
// District APIs
// =============================================================================

/**
 * Get list of all districts with tier-appropriate data
 * BASIC: Simplified geometry, aggregate AQI only
 * PREMIUM: Full geometry, pollutant breakdown, station counts
 */
export async function getDistricts(params?: {
  simplified?: boolean;
}): Promise<{ count: number; tier: string; results: DistrictListItem[] }> {
  const response = await apiClient.get('/air-quality/spatial/districts/', {
    params,
  });
  // Ensure data is properly structured
  const data = response.data || response;
  return {
    count: data?.count || 0,
    tier: data?.tier || 'BASIC',
    results: Array.isArray(data?.results) ? data.results : [],
  };
}

/**
 * Get detailed district information
 * BASIC: Name, geometry, aggregate AQI
 * PREMIUM: + pollutants, bounds, stations, trends
 */
export async function getDistrictDetail(districtId: number): Promise<DistrictDetail> {
  const response = await apiClient.get(`/air-quality/spatial/districts/${districtId}/`);
  return response.data;
}

/**
 * Get raster tile URLs for a district (PREMIUM ONLY)
 * Returns signed GCS URLs for pollutant raster tiles
 */
export async function getDistrictTiles(
  districtId: number,
  params: {
    pollutant: string;
    date?: string; // YYYY-MM-DD
  }
): Promise<{ tiles: TileInfo[] }> {
  const response = await apiClient.get(`/air-quality/spatial/districts/${districtId}/tiles/`, {
    params,
  });
  return response.data;
}

// =============================================================================
// Station APIs
// =============================================================================

/**
 * Find stations near a location
 * BASIC: 10 stations max, basic info only
 * PREMIUM: 50 stations max, latest readings included
 */
export async function getStationsNearby(params: {
  lat: number;
  lng: number;
  radius?: number; // km, default 50
  limit?: number;
}): Promise<{ count: number; tier: string; stations: StationItem[] }> {
  const response = await apiClient.get('/air-quality/spatial/stations/nearby/', {
    params,
  });
  const data = response.data || response;
  return {
    count: data?.count || 0,
    tier: data?.tier || 'BASIC',
    stations: Array.isArray(data?.stations) ? data.stations : [],
  };
}

/**
 * Get latest readings from all active stations
 */
export async function getLatestStationReadings(params?: {
  parameter?: string; // PM25, PM10, NO2, etc.
  active_only?: boolean;
}): Promise<{ count: number; results: StationItem[] }> {
  const response = await apiClient.get('/air-quality/stations/latest/', {
    params,
  });
  const data = response.data || response;
  return {
    count: data?.count || 0,
    results: Array.isArray(data?.results) ? data.results : [],
  };
}

/**
 * Get station detail with recent readings
 */
export async function getStationDetail(stationId: number): Promise<StationItem & {
  readings: Array<{
    timestamp: string;
    PM25?: number;
    PM10?: number;
    NO2?: number;
    SO2?: number;
    CO?: number;
    O3?: number;
    aqi?: number;
  }>;
}> {
  const response = await apiClient.get(`/air-quality/stations/${stationId}/`);
  return response.data;
}

/**
 * Get timeseries data for a station (for charts)
 */
export async function getStationTimeseries(
  stationId: number,
  params?: {
    parameter?: string; // PM25, PM10, NO2, etc.
    days?: number; // default 7
    interval?: 'hourly' | 'daily'; // default hourly
  }
): Promise<{
  station: StationItem;
  parameter: string;
  interval: string;
  data: Array<{
    timestamp: string;
    value: number;
  }>;
}> {
  const response = await apiClient.get(`/air-quality/stations/${stationId}/timeseries/`, {
    params,
  });
  return response.data;
}

// =============================================================================
// GEE (Google Earth Engine) APIs
// =============================================================================

/**
 * Get available dates for a pollutant in GEE
 */
export async function getGEEDates(pollutant: string): Promise<{
  pollutant: string;
  dates: string[]; // YYYY-MM-DD
  latest: string;
}> {
  const response = await apiClient.get('/air-quality/gee/dates/', {
    params: { pollutant },
  });
  return response.data;
}

/**
 * Get GEE tile URL for a pollutant and date
 */
export async function getGEETiles(params: {
  pollutant: string;
  date: string; // YYYY-MM-DD
}): Promise<{
  pollutant: string;
  date: string;
  tile_url: string;
  bounds: [number, number, number, number];
}> {
  const response = await apiClient.get('/air-quality/gee/tiles/', {
    params,
  });
  return response.data;
}

// =============================================================================
// Exposure APIs
// =============================================================================

/**
 * Get population exposure data for districts
 */
export async function getDistrictExposure(params?: {
  date?: string; // YYYY-MM-DD
  pollutant?: string;
  province?: string;
}): Promise<{
  count: number;
  results: Array<{
    district_id: number;
    district_name: string;
    province: string;
    date: string;
    pollutant: string;
    mean_exposure: number;
    population_exposed: number;
    aqi: number;
    aqi_category: string;
  }>;
}> {
  const response = await apiClient.get('/exposure/districts/', {
    params,
  });
  const data = response.data || response;
  return {
    count: data?.count || 0,
    results: Array.isArray(data?.results) ? data.results : [],
  };
}

export default {
  getDistricts,
  getDistrictDetail,
  getDistrictTiles,
  getStationsNearby,
  getLatestStationReadings,
  getStationDetail,
  getStationTimeseries,
  getGEEDates,
  getGEETiles,
  getDistrictExposure,
};
