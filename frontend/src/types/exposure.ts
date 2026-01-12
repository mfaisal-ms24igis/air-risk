/**
 * Exposure Types
 * 
 * TypeScript interfaces for exposure analytics API responses.
 * 
 * @module types/exposure
 */

import type { FeatureCollection, Polygon, MultiPolygon } from 'geojson';

// =============================================================================
// AQI Types
// =============================================================================

/**
 * AQI Category values
 */
export type AQICategory = 
  | 'Good'
  | 'Moderate'
  | 'Unhealthy for Sensitive Groups'
  | 'Unhealthy'
  | 'Very Unhealthy'
  | 'Hazardous';

/**
 * AQI color hex code
 */
export type AQIColor = string;

// =============================================================================
// District Exposure
// =============================================================================

/**
 * District exposure data from /api/v1/exposure/districts/
 */
export interface DistrictExposure {
  id: number;
  district_id: number;
  district_name: string;
  province: string;
  date: string;
  
  // Air quality metrics
  mean_pm25: number | null;
  mean_aqi: number | null;
  exposure_index: number | null;
  
  // Population data
  total_population: number | null;
  pop_good: number | null;
  pop_moderate: number | null;
  pop_usg: number | null;
  pop_unhealthy: number | null;
  pop_very_unhealthy: number | null;
  pop_hazardous: number | null;
  pop_at_risk: number | null;
  
  // Metadata
  data_source: string;
  aqi_color?: AQIColor;
  aqi_category?: AQICategory;
}

/**
 * Properties for district exposure GeoJSON features
 */
export interface DistrictExposureProperties {
  district_id: number;
  district_name: string;
  province: string;
  date: string;
  
  // Air quality metrics
  mean_pm25: number | null;
  mean_aqi: number | null;
  exposure_index: number | null;
  
  // Population breakdown by AQI category
  total_population: number | null;
  pop_good: number | null;
  pop_moderate: number | null;
  pop_usg: number | null;
  pop_unhealthy: number | null;
  pop_very_unhealthy: number | null;
  pop_hazardous: number | null;
  pop_at_risk: number | null;
  
  // Styling helpers
  data_source: string;
  aqi_color: string;
  aqi_category: string;
  
  [key: string]: unknown;
}

/**
 * GeoJSON FeatureCollection for district exposure
 */
export type DistrictExposureGeoJSON = FeatureCollection<
  Polygon | MultiPolygon,
  DistrictExposureProperties
>;

// =============================================================================
// Province Exposure
// =============================================================================

/**
 * Province exposure summary
 */
export interface ProvinceExposure {
  id: number;
  province_name: string;
  date: string;
  
  // Aggregated metrics
  total_population: number;
  mean_pm25: number | null;
  mean_aqi: number | null;
  exposure_index: number | null;
  
  // District counts
  district_count: number;
  districts_at_risk: number;
  
  // Population breakdown
  pop_good: number;
  pop_moderate: number;
  pop_usg: number;
  pop_unhealthy: number;
  pop_very_unhealthy: number;
  pop_hazardous: number;
  pop_at_risk: number;
}

// =============================================================================
// National Exposure
// =============================================================================

/**
 * National exposure summary from /api/v1/exposure/national/
 */
export interface NationalExposure {
  id: number;
  date: string;
  
  // Aggregated metrics
  total_population: number;
  mean_pm25: number | null;
  mean_aqi: number | null;
  exposure_index: number | null;
  
  // Population breakdown
  pop_good: number;
  pop_moderate: number;
  pop_usg: number;
  pop_unhealthy: number;
  pop_very_unhealthy: number;
  pop_hazardous: number;
  pop_at_risk: number;
  pop_at_risk_pct: number;
  
  // Province/district counts
  province_count: number;
  district_count: number;
}

// =============================================================================
// National Dashboard
// =============================================================================

/**
 * National exposure summary from /api/v1/exposure/dashboard/
 */
export interface DashboardData {
  national: {
    date: string;
    total_population: number;
    mean_pm25: number;
    mean_aqi: number;
    exposure_index: number;
    pop_at_risk: number;
    pop_at_risk_pct: number;
  };
  
  provinces: ProvinceExposure[];
  
  worst_districts: {
    district_id: number;
    district_name: string;
    province: string;
    mean_pm25: number;
    mean_aqi: number;
    population: number;
  }[];
  
  hotspots: {
    id: number;
    name: string;
    province: string;
    mean_pm25: number;
    pop_at_risk: number;
  }[];
}

// =============================================================================
// Trends
// =============================================================================

/**
 * Exposure trend data point
 */
export interface TrendDataPoint {
  date: string;
  mean_pm25: number;
  mean_aqi: number;
  pop_at_risk: number;
  exposure_index: number;
}

/**
 * Exposure trends response
 */
export interface ExposureTrends {
  scope: 'national' | 'province' | 'district';
  scope_name?: string;
  period: {
    start: string;
    end: string;
    days: number;
  };
  data: TrendDataPoint[];
}

// =============================================================================
// Hotspots
// =============================================================================

/**
 * Air quality hotspot
 */
export interface Hotspot {
  id: number;
  district_id: number;
  district_name: string;
  province: string;
  date: string;
  mean_pm25: number;
  mean_aqi: number;
  pop_at_risk: number;
  exposure_index: number;
  severity: 'moderate' | 'high' | 'severe' | 'critical';
}

// =============================================================================
// AQI Legend
// =============================================================================

/**
 * AQI legend category
 */
export interface AQILegendCategory {
  category: string;
  short_name?: string;
  range: { min: number; max: number };
  color: string;
  description: string;
  health_message: string;
}

/**
 * Pollutant info
 */
export interface PollutantInfo {
  code: string;
  name: string;
  full_name: string;
  unit: string;
  description: string;
}

/**
 * AQI legend response from /api/v1/air-quality/legend/
 */
export interface AQILegend {
  categories: AQILegendCategory[];
  pollutants: PollutantInfo[];
  source: string;
}
