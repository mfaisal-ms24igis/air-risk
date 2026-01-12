/**
 * Hook for fetching satellite exposure data for a location
 * Uses the newer /api/v1/exposure/satellite/ endpoint
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

export interface SatelliteExposureMetrics {
  mean_pm25: number | null;
  mean_aqi: number | null;
  exposure_index: number | null;
  pop_at_risk: number | null;
  data_source: string;
}

export interface SatelliteExposureResponse {
  target_date: string;
  days_back: number;
  location: {
    type: 'point' | 'bbox' | 'city';
    lat?: number;
    lon?: number;
    bounds?: [number, number, number, number];
    name?: string;
  };
  exposure: SatelliteExposureMetrics;
}

export interface SatelliteExposureParams {
  /** Latitude */
  lat?: number;
  /** Longitude */
  lon?: number;
  /** Bounding box [minx, miny, maxx, maxy] */
  bbox?: [number, number, number, number];
  /** City name */
  city?: string;
  /** Target date YYYY-MM-DD */
  date?: string;
  /** Days to look back (default: 7) */
  daysBack?: number;
}

/**
 * Fetch satellite exposure for a point or bbox location
 * 
 * Endpoint: GET /api/v1/exposure/satellite/
 * 
 * @example
 * ```tsx
 * const { data } = useSatelliteExposure({
 *   lat: 31.5204,
 *   lon: 74.3587,
 *   daysBack: 7
 * });
 * ```
 */
export function useSatelliteExposure(
  params: SatelliteExposureParams,
  options?: Omit<UseQueryOptions<SatelliteExposureResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['satellite-exposure', params],
    queryFn: async () => {
      const queryParams = new URLSearchParams();

      if (params.lat !== undefined && params.lon !== undefined) {
        queryParams.append('lat', params.lat.toString());
        queryParams.append('lon', params.lon.toString());
      } else if (params.bbox) {
        queryParams.append('minx', params.bbox[0].toString());
        queryParams.append('miny', params.bbox[1].toString());
        queryParams.append('maxx', params.bbox[2].toString());
        queryParams.append('maxy', params.bbox[3].toString());
      } else if (params.city) {
        queryParams.append('city', params.city);
      }

      if (params.date) {
        queryParams.append('date', params.date);
      }

      if (params.daysBack) {
        queryParams.append('days_back', params.daysBack.toString());
      }

      const response = await axios.get<SatelliteExposureResponse>(
        `${API_BASE}/exposure/satellite/?${queryParams.toString()}`
      );

      return response.data;
    },
    enabled: !!(params.lat || params.bbox || params.city),
    ...options,
  });
}

export default useSatelliteExposure;
