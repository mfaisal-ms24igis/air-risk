/**
 * Backend Model TypeScript Interfaces
 * 
 * Type definitions matching Django models from the backend.
 * These provide type safety for API responses throughout the application.
 * 
 * @module types/models
 */

// =============================================================================
// Administrative Boundaries
// =============================================================================

/**
 * Province model from Django
 * Represents administrative province with geometry
 */
export interface Province {
  id: number;
  name: string;
  population?: number;
  area_km2?: number;
  created_at?: string;
  updated_at?: string;
}

/**
 * Province properties for GeoJSON features
 */
export interface ProvinceProperties {
  id: number;
  name: string;
  population?: number;
  area_km2?: number;
  [key: string]: unknown;
}

/**
 * District model from Django
 * Represents administrative district with geometry
 */
export interface District {
  id: number;
  name: string;
  province: string;
  province_id?: number;
  population?: number;
  area_km2?: number;
  created_at?: string;
  updated_at?: string;
}

/**
 * District properties for GeoJSON features
 */
export interface DistrictProperties extends Record<string, unknown> {
  id: number;
  name: string;
  province: string;
  province_id?: number;
  population?: number;
  area_km2?: number;
  pm25_mean?: number;
  pm10_mean?: number;
  aqi?: number;
  risk_level?: RiskLevel;
}

// =============================================================================
// Air Quality Stations
// =============================================================================

/**
 * Station priority levels matching Django IntegerChoices
 */
export enum StationPriority {
  CRITICAL = 1,
  HIGH = 2,
  MEDIUM = 3,
  LOW = 4,
  MINIMAL = 5,
}

/**
 * Data source options for stations
 */
export type DataSource = 'OPENAQ' | 'MANUAL' | 'GOV' | 'RESEARCH';

/**
 * AirQualityStation model from Django
 * Ground-based air quality monitoring station
 */
export interface AirQualityStation {
  id: number;
  openaq_location_id: number;
  openaq_id?: string;
  name: string;
  latitude: number;
  longitude: number;
  location?: {
    lat: number;
    lng: number;
  };
  district?: District | null;
  district_id?: number | null;
  locality?: string;
  city?: string;
  country: string;
  timezone: string;
  data_source: DataSource;
  available_parameters: string[];
  sensors_count: number;
  priority: StationPriority;
  is_active: boolean;
  last_reading_at?: string | null;
  total_readings: number;
  created_at: string;
  updated_at: string;
}

/**
 * Station properties for GeoJSON features
 */
export interface StationProperties extends Record<string, unknown> {
  id: number;
  name: string;
  openaq_location_id: number;
  latitude: number;
  longitude: number;
  district?: string;
  city?: string;
  is_active: boolean;
  available_parameters: string[];
  last_reading_at?: string | null;
  // Latest readings (if included)
  pm25?: number | null;
  pm10?: number | null;
  no2?: number | null;
  so2?: number | null;
  co?: number | null;
  o3?: number | null;
}

// =============================================================================
// Pollutant Readings
// =============================================================================

/**
 * Pollutant parameter codes
 */
export type PollutantCode = 'PM25' | 'PM10' | 'NO2' | 'SO2' | 'CO' | 'O3';

/**
 * PollutantReading model from Django
 * Individual air quality reading from a station
 */
export interface PollutantReading {
  id: number;
  station_id: number;
  timestamp: string;
  parameter: PollutantCode;
  value: number;
  unit: string;
  created_at?: string;
}

/**
 * Time series data point for charts
 */
export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
  parameter: PollutantCode;
}

// =============================================================================
// Exposure Analysis
// =============================================================================

/**
 * Risk level categories
 */
export type RiskLevel = 'low' | 'moderate' | 'high' | 'very_high' | 'hazardous';

/**
 * Data source for exposure calculations
 */
export type ExposureDataSource = 'satellite' | 'ground' | 'fused' | 'raster';

/**
 * DistrictExposure model from Django
 * Daily population exposure statistics for a district
 */
export interface DistrictExposure {
  id: number;
  district_id: number;
  district_name?: string;
  pollutant?: PollutantCode | null;
  date: string;
  total_population: number;
  pop_good: number;
  pop_moderate: number;
  pop_usg: number;
  pop_unhealthy: number;
  pop_very_unhealthy: number;
  pop_hazardous: number;
  mean_pm25?: number | null;
  max_pm25?: number | null;
  mean_aqi?: number | null;
  max_aqi?: number | null;
  exposure_index?: number | null;
  rank?: number | null;
  data_source: ExposureDataSource;
  station_count: number;
}

/**
 * Hotspot severity levels
 */
export type HotspotSeverity = 'MODERATE' | 'HIGH' | 'SEVERE' | 'CRITICAL';

/**
 * Hotspot model from Django
 * Geographic hotspot of high air pollution
 */
export interface Hotspot {
  id: number;
  pollutant?: PollutantCode | null;
  date: string;
  centroid: {
    type: 'Point';
    coordinates: [number, number]; // [lng, lat]
  };
  geometry?: {
    type: 'Polygon';
    coordinates: number[][][];
  } | null;
  area_sq_km?: number | null;
  severity: HotspotSeverity;
  affected_population: number;
  peak_concentration: number;
  districts?: string[];
}

// =============================================================================
// AQI Reference Data
// =============================================================================

/**
 * AQI category from legend endpoint
 */
export interface AQICategory {
  category: string;
  short_name?: string;
  range: {
    min: number;
    max: number;
  };
  color: string;
  description: string;
  health_message: string;
}

/**
 * Pollutant reference info
 */
export interface PollutantInfo {
  code: PollutantCode;
  name: string;
  full_name: string;
  unit: string;
  description: string;
}

/**
 * AQI Legend response
 */
export interface AQILegend {
  categories: AQICategory[];
  pollutants: PollutantInfo[];
  source: string;
}

// =============================================================================
// GEE Layer Configuration
// =============================================================================

/**
 * GEE Sentinel-5P layer configuration
 */
export interface GEELayerConfig {
  code: string;
  title: string;
  description: string;
  unit: string;
  min_val: number;
  max_val: number;
  palette: string[];
}

/**
 * GEE Tile URL response
 */
export interface GEETileResponse {
  pollutant: string;
  date: string;
  tile_url: string;
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

// =============================================================================
// Dashboard & Analytics
// =============================================================================

/**
 * Exposure dashboard summary
 */
export interface ExposureDashboard {
  date: string;
  total_population: number;
  population_at_risk: number;
  percent_at_risk: number;
  top_districts: DistrictExposure[];
  active_hotspots: number;
  avg_aqi: number;
  data_freshness: string;
}

/**
 * Station statistics summary
 */
export interface StationStats {
  total_stations: number;
  active_stations: number;
  readings_today: number;
  avg_pm25: number | null;
  last_sync: string;
}
