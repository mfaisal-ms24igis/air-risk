/**
 * Dynamic Pixel-Wise Air Quality Risk Service
 * 
 * Fetches hybrid local + GEE risk tiles and manages visualization
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface RiskLegendStop {
  value: number;
  color: string;
  label: string;
}

export interface RiskLegend {
  title: string;
  subtitle: string;
  unit: string;
  stops: RiskLegendStop[];
  min: number;
  max: number;
}

export interface RiskMetadata {
  sentinel5p_date: string;
  openaq_points: number;
  worldpop_year: number;
  risk_min: number;
  risk_max: number;
  bbox: {
    min_lon: number;
    min_lat: number;
    max_lon: number;
    max_lat: number;
  };
  fusion_method: string;
  fusion_weights: {
    ground: number;
    satellite: number;
  };
  generated_at: string;
}

export interface RiskTilesResponse {
  success: boolean;
  tile_url: string;
  map_id: string;
  token: string;
  legend: RiskLegend;
  metadata: RiskMetadata;
  request_params: {
    days: number;
    sentinel_days_back: number;
    pollutant: string;
  };
  error?: string;
  error_type?: string;
}

export interface RiskStatusResponse {
  success: boolean;
  status: {
    image_date: string;
    last_check: string;
    is_new: boolean;
    check_interval_hours: number;
  } | null;
  is_healthy: boolean;
  last_checked: string;
  last_changed: string;
  error_message?: string;
}

/**
 * Fetch GEE tile URL and legend for risk visualization
 */
export async function getRiskTiles(params?: {
  days?: number;
  sentinel_days_back?: number;
  pollutant?: string;
}): Promise<RiskTilesResponse> {
  const queryParams = new URLSearchParams({
    days: String(params?.days || 7),
    sentinel_days_back: String(params?.sentinel_days_back || 30),
    pollutant: params?.pollutant || 'pm25',
  });

  const response = await axios.get(
    `${API_BASE}/api/v1/air-quality/risk/tiles/?${queryParams}`
  );

  return response.data;
}

/**
 * Check Sentinel-5P update status
 */
export async function getRiskStatus(): Promise<RiskStatusResponse> {
  const response = await axios.get(
    `${API_BASE}/api/v1/air-quality/risk/status/`
  );

  return response.data;
}

/**
 * Manually trigger a Sentinel-5P check (for testing)
 */
export async function triggerManualCheck(): Promise<any> {
  const response = await axios.post(
    `${API_BASE}/api/v1/air-quality/risk/check/`
  );

  return response.data;
}
