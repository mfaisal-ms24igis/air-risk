/**
 * Query Hooks Barrel Export
 * 
 * Centralized export of all TanStack Query hooks.
 * 
 * @module hooks/queries
 */

// Stations
export {
  stationKeys,
  useStations,
  useStation,
  useStationsGeoJSON,
  useStationReadings,
  useStationTimeSeries,
  useNearbyStations,
  prefetchStations,
  prefetchStation,
  type StationsResponse,
  type StationsGeoJSON,
  type ReadingsResponse,
  type TimeSeriesResponse,
} from './useStations';
export type { StationFilters as StationsFilters } from '@/types/api';

// Districts
export {
  districtKeys,
  useDistricts,
  useDistrict,
  useDistrictsGeoJSON,
  type DistrictsResponse,
  type DistrictsGeoJSON,
} from './useDistricts';
export type { DistrictFilters as DistrictsFilters } from '@/types/api';

// Provinces
export {
  provinceKeys,
  useProvinces,
  useProvince,
  useProvincesGeoJSON,
  type ProvincesResponse,
  type ProvincesGeoJSON,
} from './useProvinces';

// Spatial Data (new tiered APIs)
export * from './useSpatialData';

// Exposure (PM2.5, AQI, population at risk)
export {
  exposureKeys,
  useDashboard,
  useDistrictExposures,
  useDistrictExposure,
  useDistrictExposureGeoJSON,
  useProvinceExposures,
  useNationalExposure,
  useHotspots,
  useExposureTrends,
} from './useExposure';

// Satellite Exposure (location-based exposure from satellite data)
export {
  useSatelliteExposure,
  type SatelliteExposureResponse,
  type SatelliteExposureParams,
} from './useSatelliteExposure';

// GEE (Google Earth Engine - Sentinel-5P satellite data)
export {
  geeKeys,
  useGEELayers,
  useGEETiles,
  useGEEDates,
  prefetchGEELayers,
  prefetchGEETiles,
  type GEEPollutant,
  type GEELayerConfig,
  type GEETileResponse,
  type GEEDatesResponse,
} from './useGEE';

// WMS (GeoServer WMS layers)
export {
  wmsKeys,
  useWMSLayers,
  useWMSTimeSeries,
  prefetchWMSLayers,
  type WMSLayerConfig,
  type WMSTimeSeriesResponse,
  type WMSLayersParams,
} from './useWMS';

// Legend & Reference Data (AQI colors, health messages)
export {
  legendKeys,
  useAQILegend,
  getAQICategory,
  getAQIColor,
  getPM25Category,
  prefetchAQILegend,
  type AQICategory,
  type PM25Breakpoint,
  type AQILegendResponse,
} from './useLegend';
