/**
 * Districts API Service
 * 
 * Handles fetching district list for GEE exposure calculations.
 */

import apiClient from './client';
import type { GeoJSONFeatureCollection } from '@/types/geojson-strict';

export interface District {
  id: number;
  name: string;
  province: string;
  population?: number;
  area_km2?: number;
  geometry?: any; // GeoJSON geometry
}

export interface DistrictsResponse {
  count: number;
  tier: string;
  results: District[];
}

/**
 * Get list of all districts.
 */
export async function getDistricts(): Promise<District[]> {
  // Use unknown first, then narrow down safely
  const response = await apiClient.get<unknown>('/air-quality/spatial/districts/');
  console.log('[Districts API] Raw response:', response);

  // Helper type guard
  const isFeatureCollection = (data: any): data is GeoJSONFeatureCollection<any, District> => {
    return data && data.type === 'FeatureCollection' && Array.isArray(data.features);
  };

  // 1. Check if response itself is FeatureCollection
  if (isFeatureCollection(response)) {
    console.log('[Districts API] Parsing FeatureCollection from root');
    return response.features.map(f => ({
      ...f.properties,
      id: Number(f.id),
      geometry: f.geometry
    }));
  }

  // 2. Check if nested in 'results' (DRF Pagination + GeoJSON)
  const nestedData = (response as any).results;
  if (nestedData) {
    if (isFeatureCollection(nestedData)) {
      console.log('[Districts API] Parsing FeatureCollection from results.features');
      return nestedData.features.map(f => ({
        ...f.properties,
        id: Number(f.id),
        geometry: f.geometry
      }));
    }
    if (Array.isArray(nestedData)) {
      console.log('[Districts API] Returning results array');
      return nestedData as District[];
    }
  }

  // 3. Check if 'data' wrapper exists (legacy wrapper)
  const dataWrapper = (response as any).data;
  if (dataWrapper && isFeatureCollection(dataWrapper)) {
    console.log('[Districts API] Parsing FeatureCollection from data');
    return dataWrapper.features.map(f => ({
      ...f.properties,
      id: Number(f.id),
      geometry: f.geometry
    }));
  }

  console.warn('[Districts API] Unexpected response format:', response);
  return [];
}
