/**
 * GeoJSON TypeScript Interfaces
 * Strictly typed for autocomplete and type safety
 */

// ============================================
// GeoJSON Geometry Types
// ============================================

export type GeoJSONGeometryType =
  | 'Point'
  | 'MultiPoint'
  | 'LineString'
  | 'MultiLineString'
  | 'Polygon'
  | 'MultiPolygon'
  | 'GeometryCollection';

export interface GeoJSONPosition {
  0: number; // longitude
  1: number; // latitude
  2?: number; // altitude (optional)
}

export interface PointGeometry {
  type: 'Point';
  coordinates: [number, number] | [number, number, number];
}

export interface MultiPointGeometry {
  type: 'MultiPoint';
  coordinates: Array<[number, number] | [number, number, number]>;
}

export interface LineStringGeometry {
  type: 'LineString';
  coordinates: Array<[number, number] | [number, number, number]>;
}

export interface MultiLineStringGeometry {
  type: 'MultiLineString';
  coordinates: Array<Array<[number, number] | [number, number, number]>>;
}

export interface PolygonGeometry {
  type: 'Polygon';
  coordinates: Array<Array<[number, number] | [number, number, number]>>;
}

export interface MultiPolygonGeometry {
  type: 'MultiPolygon';
  coordinates: Array<Array<Array<[number, number] | [number, number, number]>>>;
}

export type GeoJSONGeometry =
  | PointGeometry
  | MultiPointGeometry
  | LineStringGeometry
  | MultiLineStringGeometry
  | PolygonGeometry
  | MultiPolygonGeometry;

// ============================================
// GeoJSON Feature Types
// ============================================

export interface GeoJSONFeature<
  G extends GeoJSONGeometry = GeoJSONGeometry,
  P extends Record<string, unknown> = Record<string, unknown>
> {
  type: 'Feature';
  id?: string | number;
  geometry: G;
  properties: P;
  bbox?: [number, number, number, number] | [number, number, number, number, number, number];
}

export interface GeoJSONFeatureCollection<
  G extends GeoJSONGeometry = GeoJSONGeometry,
  P extends Record<string, unknown> = Record<string, unknown>
> {
  type: 'FeatureCollection';
  features: Array<GeoJSONFeature<G, P>>;
  bbox?: [number, number, number, number] | [number, number, number, number, number, number];
}

// ============================================
// Domain-Specific Property Types (Re-export from models)
// ============================================

// Import property interfaces from models to avoid duplication
import type { DistrictProperties, ProvinceProperties, StationProperties } from './models';

export type { DistrictProperties, ProvinceProperties, StationProperties };

export interface GridCellProperties {
  id: number;
  row: number;
  col: number;
  value?: number;
  parameter?: string;
  date?: string;
  [key: string]: unknown; // Index signature for GeoJSON compatibility
}

// ============================================
// Typed Feature Collections
// ============================================

export type DistrictFeature = GeoJSONFeature<PolygonGeometry | MultiPolygonGeometry, DistrictProperties>;
export type DistrictFeatureCollection = GeoJSONFeatureCollection<PolygonGeometry | MultiPolygonGeometry, DistrictProperties>;

export type ProvinceFeature = GeoJSONFeature<PolygonGeometry | MultiPolygonGeometry, ProvinceProperties>;
export type ProvinceFeatureCollection = GeoJSONFeatureCollection<PolygonGeometry | MultiPolygonGeometry, ProvinceProperties>;

export type StationFeature = GeoJSONFeature<PointGeometry, StationProperties>;
export type StationFeatureCollection = GeoJSONFeatureCollection<PointGeometry, StationProperties>;

export type GridFeature = GeoJSONFeature<PolygonGeometry, GridCellProperties>;
export type GridFeatureCollection = GeoJSONFeatureCollection<PolygonGeometry, GridCellProperties>;
