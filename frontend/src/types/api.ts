/**
 * API Response Types
 * 
 * Type definitions for the Django REST Framework API envelope format.
 * All API responses follow this consistent structure.
 * 
 * @module types/api
 */

import type { FeatureCollection, Geometry, GeoJsonProperties } from 'geojson';

// =============================================================================
// API Envelope Types
// =============================================================================

/**
 * Standard success response envelope from Django
 */
export interface ApiSuccessResponse<T = unknown> {
  status: 'success';
  data: T;
  message: string;
}

/**
 * Standard error response envelope from Django
 */
export interface ApiErrorResponse {
  status: 'error';
  data: null;
  message: string;
  errors?: Record<string, string[]>;
}

/**
 * Union type for all API responses
 */
export type ApiResponse<T = unknown> = ApiSuccessResponse<T> | ApiErrorResponse;

/**
 * Type guard to check if response is successful
 */
export function isSuccessResponse<T>(
  response: ApiResponse<T>
): response is ApiSuccessResponse<T> {
  return response.status === 'success';
}

/**
 * Type guard to check if response is an error
 */
export function isErrorResponse(
  response: ApiResponse<unknown>
): response is ApiErrorResponse {
  return response.status === 'error';
}

// =============================================================================
// Normalized Error Type
// =============================================================================

/**
 * Normalized error structure for consistent error handling
 */
export interface ApiError {
  status: 'error';
  message: string;
  code?: string;
  statusCode?: number;
  errors?: Record<string, string[]>;
  timestamp: string;
  originalError?: unknown;
}

/**
 * Create a normalized ApiError from various error types
 */
export function createApiError(
  message: string,
  options?: Partial<Omit<ApiError, 'status' | 'message' | 'timestamp'>>
): ApiError {
  return {
    status: 'error',
    message,
    timestamp: new Date().toISOString(),
    ...options,
  };
}

// =============================================================================
// GeoJSON Response Types
// =============================================================================

/**
 * GeoJSON FeatureCollection response type with custom properties
 */
export type GeoJSONResponse<P extends GeoJsonProperties = GeoJsonProperties> = 
  FeatureCollection<Geometry, P>;

// =============================================================================
// Pagination Types
// =============================================================================

/**
 * Paginated response from DRF
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Pagination parameters for requests
 */
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

// =============================================================================
// Filter Types
// =============================================================================

/**
 * Common filter parameters for district queries
 */
export interface DistrictFilters {
  province?: string;
  name?: string;
  [key: string]: unknown; // Allow additional query params
}

/**
 * Filter parameters for station queries
 */
export interface StationFilters {
  district?: number;
  province?: string;
  is_active?: boolean;
  source?: string;
  [key: string]: unknown; // Allow additional query params
}

/**
 * Filter parameters for readings queries
 */
export interface ReadingsFilters {
  station_id?: number;
  parameter?: string;
  days?: number;
  start_date?: string;
  end_date?: string;
}

// =============================================================================
// GEE Types
// =============================================================================

/**
 * GEE Layer configuration
 */
export interface GEELayer {
  code: string;
  name: string;
  description: string;
  unit: string;
  min_value: number;
  max_value: number;
  color_palette: string[];
}

/**
 * GEE Tile URL response
 */
export interface GEETileResponse {
  tile_url: string;
  pollutant: string;
  date: string;
  bounds?: {
    west: number;
    south: number;
    east: number;
    north: number;
  };
  legend?: {
    min: number;
    max: number;
    palette: string[];
    unit: string;
  };
}

/**
 * GEE tiles request parameters
 */
export interface GEETilesParams {
  pollutant: string;
  date: string;
}

/**
 * Nearby stations request parameters
 */
export interface NearbyStationsParams {
  lat: number;
  lon: number;
  radius?: number;
  [key: string]: unknown; // Allow additional query params
}

/**
 * Time series request parameters
 */
export interface TimeSeriesParams {
  parameter: string;
  interval?: 'hourly' | 'daily' | 'weekly' | 'monthly';
  days?: number;
  [key: string]: unknown; // Allow additional query params
}

// Station Timeseries
export interface TimeseriesDataPoint {
  datetime: string;
  value: number;
  parameter: string;
}

export interface StationTimeseries {
  station_id: number;
  station_name: string;
  parameter: string;
  unit: string;
  data: TimeseriesDataPoint[];
}

// Exposure data
export interface ExposureStats {
  district_id: number;
  district_name: string;
  population: number;
  pm25_mean: number;
  pm25_max: number;
  exposed_population: number;
  exposure_percentage: number;
}
