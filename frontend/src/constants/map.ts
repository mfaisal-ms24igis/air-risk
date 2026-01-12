/**
 * Map Constants and Configuration
 * 
 * Centralized constants for map visualization, legends, and colors.
 */

// =============================================================================
// AQI Legend Items
// =============================================================================

export const LEGEND_ITEMS = [
  { min: 0, max: 50, label: 'Good', color: '#00E400' },
  { min: 51, max: 100, label: 'Moderate', color: '#FFFF00' },
  { min: 101, max: 150, label: 'Unhealthy FSG', color: '#FF7E00' },
  { min: 151, max: 200, label: 'Unhealthy', color: '#FF0000' },
  { min: 201, max: 300, label: 'Very Unhealthy', color: '#8F3F97' },
  { min: 301, max: 500, label: 'Hazardous', color: '#7E0023' },
] as const;

// =============================================================================
// PM2.5 Legend Items
// =============================================================================

export const PM25_LEGEND_ITEMS = [
  { min: 0, max: 12, label: 'Good', color: '#00E400' },
  { min: 12.1, max: 35.4, label: 'Moderate', color: '#FFFF00' },
  { min: 35.5, max: 55.4, label: 'Unhealthy FSG', color: '#FF7E00' },
  { min: 55.5, max: 150.4, label: 'Unhealthy', color: '#FF0000' },
  { min: 150.5, max: 250.4, label: 'Very Unhealthy', color: '#8F3F97' },
  { min: 250.5, max: 500, label: 'Hazardous', color: '#7E0023' },
] as const;

// =============================================================================
// Exposure Color Scale
// =============================================================================

export const EXPOSURE_COLORS = [
  '#00FF00', // Green (low exposure)
  '#FFFF00', // Yellow
  '#FFA500', // Orange
  '#FF0000', // Red
  '#800080', // Purple
  '#400020', // Dark red (high exposure)
] as const;

// =============================================================================
// Map Style URLs
// =============================================================================

export const MAP_STYLES = {
  STREETS: 'https://api.maptiler.com/maps/streets-v2/style.json',
  SATELLITE: 'https://api.maptiler.com/maps/hybrid/style.json',
  LIGHT: 'https://api.maptiler.com/maps/basic-v2-light/style.json',
  DARK: 'https://api.maptiler.com/maps/basic-v2-dark/style.json',
} as const;

// =============================================================================
// Default Map Bounds (Pakistan)
// =============================================================================

export const PAKISTAN_BOUNDS: [number, number, number, number] = [
  60.872, // West (longitude)
  23.635, // South (latitude)
  77.839, // East (longitude)
  37.085, // North (latitude)
];

export const PAKISTAN_CENTER: [number, number] = [
  69.3451, // Longitude
  30.3753, // Latitude
];

// =============================================================================
// Map Configuration
// =============================================================================

export const DEFAULT_ZOOM = 5;
export const MIN_ZOOM = 4;
export const MAX_ZOOM = 18;

export const CLUSTER_RADIUS = 50; // pixels
export const CLUSTER_MAX_ZOOM = 14;

// =============================================================================
// Layer Z-Index (Stacking Order)
// =============================================================================

export const LAYER_Z_INDEX = {
  BASE: 0,
  PROVINCES: 100,
  DISTRICTS: 200,
  SATELLITE: 300,
  GEE_EXPOSURE: 350,
  STATIONS: 400,
  POPUPS: 1000,
  CONTROLS: 2000,
  MODALS: 3000,
} as const;

// =============================================================================
// Color Utilities
// =============================================================================

/**
 * Get AQI color based on value.
 */
export function getAQIColor(aqi: number): string {
  for (const item of LEGEND_ITEMS) {
    if (aqi >= item.min && aqi <= item.max) {
      return item.color;
    }
  }
  return LEGEND_ITEMS[LEGEND_ITEMS.length - 1].color; // Default to hazardous
}

/**
 * Get PM2.5 color based on value.
 */
export function getPM25Color(pm25: number): string {
  for (const item of PM25_LEGEND_ITEMS) {
    if (pm25 >= item.min && pm25 <= item.max) {
      return item.color;
    }
  }
  return PM25_LEGEND_ITEMS[PM25_LEGEND_ITEMS.length - 1].color;
}

/**
 * Get AQI category label.
 */
export function getAQILabel(aqi: number): string {
  for (const item of LEGEND_ITEMS) {
    if (aqi >= item.min && aqi <= item.max) {
      return item.label;
    }
  }
  return 'Hazardous';
}

/**
 * Calculate district center from geometry.
 */
export function calculateDistrictCenter(
  geometry: any
): [number, number] | null {
  try {
    // For Polygon, get centroid of first ring
    if (geometry.type === 'Polygon' && geometry.coordinates?.[0]) {
      const ring = geometry.coordinates[0];
      if (ring.length > 0) {
        let sumLng = 0,
          sumLat = 0;
        ring.forEach((coord: number[]) => {
          sumLng += coord[0];
          sumLat += coord[1];
        });
        return [sumLng / ring.length, sumLat / ring.length];
      }
    }

    // For MultiPolygon, get first polygon's centroid
    if (geometry.type === 'MultiPolygon' && geometry.coordinates?.[0]?.[0]) {
      const ring = geometry.coordinates[0][0];
      if (ring.length > 0) {
        let sumLng = 0,
          sumLat = 0;
        ring.forEach((coord: number[]) => {
          sumLng += coord[0];
          sumLat += coord[1];
        });
        return [sumLng / ring.length, sumLat / ring.length];
      }
    }
  } catch (error) {
    console.error('[Map Utils] Error calculating district center:', error);
  }

  return null;
}
