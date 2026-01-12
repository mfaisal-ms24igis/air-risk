/**
 * ProvincesLayer Component
 * 
 * Displays province boundaries as a fill layer with drill-down capability.
 * Uses TanStack Query for data fetching with automatic caching.
 * 
 * @module components/layers/ProvincesLayer
 */

import { GeoJSONLayer } from '@/components/map';
import { useProvincesGeoJSON } from '@/hooks';

// =============================================================================
// Types
// =============================================================================

/**
 * Province feature properties from API
 */
export interface ProvinceProperties {
  id: number;
  name: string;
  total_districts?: number;
  population?: number;
  area_km2?: number;
}

export interface ProvincesLayerProps {
  /** Whether layer is visible */
  visible?: boolean;
  /** Callback when a province is clicked */
  onProvinceClick?: (province: ProvinceProperties) => void;
  /** Callback when hovering over a province */
  onProvinceHover?: (province: ProvinceProperties | null) => void;
}

// =============================================================================
// Layer Styles
// =============================================================================

// Outline only - no fill
const provinceOutlineStyle = {
  type: 'line' as const,
  filter: ['!=', ['get', 'name'], 'DISPUTED TERRITORY'],
  paint: {
    'line-color': '#666666',
    'line-width': 2,
    'line-opacity': 0.6,
  },
};

// Province labels
const provinceLabelsStyle = {
  type: 'symbol' as const,
  filter: ['!=', ['get', 'name'], 'DISPUTED TERRITORY'],
  layout: {
    'text-field': ['get', 'name'],
    'text-size': 12,
    'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
    'text-offset': [0, 0],
    'text-anchor': 'center',
  },
  paint: {
    'text-color': '#333333',
    'text-halo-color': '#ffffff',
    'text-halo-width': 1,
  },
};

// Disputed territory outline - faded
const disputedOutlineStyle = {
  type: 'line' as const,
  filter: ['==', ['get', 'name'], 'DISPUTED TERRITORY'],
  paint: {
    'line-color': '#999999',
    'line-width': 2,
    'line-opacity': 0.3,
    'line-dasharray': [2, 2],
  },
};

// Disputed territory labels - faded
const disputedLabelsStyle = {
  type: 'symbol' as const,
  filter: ['==', ['get', 'name'], 'DISPUTED TERRITORY'],
  layout: {
    'text-field': ['get', 'name'],
    'text-size': 12,
    'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
    'text-offset': [0, 0],
    'text-anchor': 'center',
  },
  paint: {
    'text-color': '#999999',
    'text-opacity': 0.4,
    'text-halo-color': '#ffffff',
    'text-halo-width': 1,
  },
};

// =============================================================================
// Component
// =============================================================================

export function ProvincesLayer({ onProvinceClick }: ProvincesLayerProps): JSX.Element | null {
  // Fetch province GeoJSON with TanStack Query
  const { data, isLoading, isError, error } = useProvincesGeoJSON();

  // Development logging
  if (import.meta.env.DEV) {
    if (isLoading) {
      console.debug('[ProvincesLayer] Loading provinces...');
    }
    if (isError) {
      console.error('[ProvincesLayer] Error:', error);
    }
  }

  return (
    <>
      {/* Province outline */}
      <GeoJSONLayer
        id="provinces"
        data={data as any ?? null}
        visible={true}
        layerStyle={provinceOutlineStyle as any}
        onFeatureClick={(feature) => {
          onProvinceClick?.(feature.properties as ProvinceProperties);
        }}
      />
      
      {/* Province labels */}
      <GeoJSONLayer
        id="provinces-labels"
        data={data as any ?? null}
        visible={true}
        layerStyle={provinceLabelsStyle as any}
      />

      {/* Disputed territory outline - faded */}
      <GeoJSONLayer
        id="provinces-disputed"
        data={data as any ?? null}
        visible={true}
        layerStyle={disputedOutlineStyle as any}
      />

      {/* Disputed territory labels - faded */}
      <GeoJSONLayer
        id="provinces-disputed-labels"
        data={data as any ?? null}
        visible={true}
        layerStyle={disputedLabelsStyle as any}
      />
    </>
  );
}

export default ProvincesLayer;
