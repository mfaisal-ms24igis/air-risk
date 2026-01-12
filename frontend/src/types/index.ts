/**
 * Types Barrel Export
 * 
 * Central export point for all TypeScript type definitions.
 * Import types from '@/types' throughout the application.
 * 
 * @module types
 */

// GeoJSON types (custom + @types/geojson re-exports)
export * from './geojson';

// API response and request types
export * from './api';

// Backend model types - excluding duplicates defined in exposure.ts
export type {
  Province,
  ProvinceProperties,
  District,
  DistrictProperties,
  AirQualityStation,
  StationProperties,
  RiskLevel,
  DataSource,
  StationPriority,
  HotspotSeverity,
} from './models';

// Exposure types (PM2.5, AQI, population at risk) - this takes precedence
export * from './exposure';
