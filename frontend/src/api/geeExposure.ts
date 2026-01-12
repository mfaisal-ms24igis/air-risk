/**
 * GEE Exposure API Service
 * 
 * Handles pixel-wise exposure calculation using Google Earth Engine
 * for premium tier users.
 */

import apiClient from './client';

// =============================================================================
// Types
// =============================================================================

export interface GEEExposureRequest {
  scope: 'district' | 'province' | 'national';
  district_ids?: number[];
  province?: string;
  target_date?: string; // YYYY-MM-DD
  days_back?: number;
  save_results?: boolean;
  async?: boolean;
}

export interface GEEExposureStatistics {
  total_population: number;
  mean_exposure_index: number;
  max_exposure_index: number;
  mean_aqi: number;
  max_aqi: number;
  population_breakdown: {
    good: number;
    moderate: number;
    unhealthy_sensitive: number;
    unhealthy: number;
    very_unhealthy: number;
    hazardous: number;
  };
  pollutants: {
    pm25?: number;
    no2?: number;
    so2?: number;
    co?: number;
  };
  dominant_pollutant: string;
}

export interface GEEExposureResult {
  district_id: number;
  district_name: string;
  province: string;
  exposure_tile_url: string;
  aqi_tile_url: string;
  map_id: string;
  token: string;
  statistics: GEEExposureStatistics;
  errors?: string[];
}

export interface GEEExposureResponse {
  results: GEEExposureResult[];
  calculation_date: string;
  days_averaged: number;
  data_source: string;
  saved_to_database: boolean;
}

export interface GEEExposureTaskResponse {
  task_id: string;
  status: 'processing' | 'completed';
  scope: string;
  district_count: number;
  calculation_date: string;
  message: string;
  results?: GEEExposureResponse;
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Calculate GEE-based pixel-wise exposure.
 * 
 * @param request - Calculation parameters
 * @returns Exposure results or task ID for async operations
 */
export async function calculateGEEExposure(
  request: GEEExposureRequest
): Promise<GEEExposureResponse | GEEExposureTaskResponse> {
  const response = await apiClient.post<GEEExposureResponse | GEEExposureTaskResponse>(
    '/exposure/calculate-gee/',
    request
  );
  // The response interceptor already unwraps the data
  return response as any;
}

/**
 * Check status of async GEE exposure calculation.
 * 
 * @param taskId - Task ID from async calculation
 * @returns Task status and results if complete
 */
export async function getGEEExposureTaskStatus(
  taskId: string
): Promise<GEEExposureTaskResponse> {
  const response = await apiClient.get<GEEExposureTaskResponse>(
    `/exposure/calculate-gee/?task_id=${taskId}`
  );
  return response.data;
}

/**
 * Calculate exposure for a single district (synchronous).
 * 
 * @param districtId - District ID
 * @param targetDate - Optional date (defaults to latest)
 * @param daysBack - Days to average (default: 7)
 * @returns Exposure result with tile URLs
 */
export async function calculateDistrictExposure(
  districtId: number,
  targetDate?: string,
  daysBack: number = 7
): Promise<GEEExposureResult> {
  const response = await calculateGEEExposure({
    scope: 'district',
    district_ids: [districtId],
    target_date: targetDate,
    days_back: daysBack,
    save_results: false,
    async: false,
  });

  // Extract first result from synchronous response
  if (!('task_id' in response)) {
    return (response as GEEExposureResponse).results[0];
  }

  throw new Error('Unexpected response format from GEE exposure API');
}

/**
 * Calculate exposure for all districts in a province (async).
 * 
 * @param province - Province name
 * @param targetDate - Optional date (defaults to latest)
 * @param daysBack - Days to average (default: 7)
 * @returns Task ID for polling status
 */
export async function calculateProvinceExposure(
  province: string,
  targetDate?: string,
  daysBack: number = 7
): Promise<GEEExposureTaskResponse> {
  const response = await calculateGEEExposure({
    scope: 'province',
    province,
    target_date: targetDate,
    days_back: daysBack,
    save_results: true,
    async: true,
  });

  // Return task response for async operation
  if ('task_id' in response) {
    return response as GEEExposureTaskResponse;
  }

  throw new Error('Expected async task response from GEE exposure API');
}

/**
 * Poll for task completion with automatic retry.
 * 
 * @param taskId - Task ID to poll
 * @param maxAttempts - Maximum polling attempts (default: 30)
 * @param intervalMs - Polling interval in milliseconds (default: 2000)
 * @returns Completed task results
 */
export async function pollGEEExposureTask(
  taskId: string,
  maxAttempts: number = 30,
  intervalMs: number = 2000
): Promise<GEEExposureResponse> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const status = await getGEEExposureTaskStatus(taskId);

    if (status.status === 'completed' && status.results) {
      return status.results;
    }

    // Wait before next poll
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error('Task polling timeout: calculation did not complete');
}

export default {
  calculateGEEExposure,
  getGEEExposureTaskStatus,
  calculateDistrictExposure,
  calculateProvinceExposure,
  pollGEEExposureTask,
};
