/**
 * DistrictsLayer Component
 * 
 * Displays district boundaries as a choropleth fill layer with PM2.5/AQI data.
 * Uses TanStack Query to fetch from the exposure API for actual air quality data.
 * 
 * @module components/layers/DistrictsLayer
 */

import { GeoJSONLayer } from '@/components/map';
import { useDistrictExposureGeoJSON } from '@/hooks/queries';

// =============================================================================
// Types
// =============================================================================

/**
 * District exposure properties from /api/v1/exposure/geojson/districts/
 */
export interface DistrictExposureProperties {
  id: number;
  district_id: number;
  district_name: string;
  province: string;
  date: string;
  total_population: number;
  mean_pm25: number | null;
  mean_aqi: number | null;
  exposure_index: number | null;
  pop_good: number;
  pop_moderate: number;
  pop_usg: number;
  pop_unhealthy: number;
  pop_very_unhealthy: number;
  pop_hazardous: number;
  pop_at_risk: number;
  data_source: string;
  aqi_color: string;
}

// Legacy interface for backwards compatibility
export interface DistrictProperties {
  id: number;
  name: string;
  province: string;
  province_id?: number;
  population?: number;
  area_km2?: number;
  pm25_mean?: number;
  pm10_mean?: number;
  aqi?: number;
  risk_level?: 'low' | 'moderate' | 'high' | 'very_high' | 'hazardous';
}

export interface DistrictsLayerProps {
  /** Province filter - if set, only show districts of this province */
  province?: string;
  /** Date filter - if set, show data for this date (YYYY-MM-DD) */
  date?: string;
  /** Whether layer is visible */
  visible?: boolean;
  /** Color mode - 'pm25' uses PM2.5 values, 'aqi' uses AQI values */
  colorMode?: 'pm25' | 'aqi';
  /** If set, only show this district (for detail view) */
  selectedDistrictId?: number;
  /** Callback when a district is clicked */
  onDistrictClick?: (district: DistrictExposureProperties) => void;
  /** Callback when hovering over a district */
  onDistrictHover?: (district: DistrictExposureProperties | null) => void;
}

// =============================================================================
// Component
// =============================================================================

export function DistrictsLayer({
  province,
  date,
  onDistrictClick,
  selectedDistrictId,
}: DistrictsLayerProps) {
  // Fetch district exposure GeoJSON with TanStack Query
  // This uses /api/v1/exposure/geojson/districts/ which has PM2.5/AQI data
  const { data, isLoading, isError, error } = useDistrictExposureGeoJSON({
    province,
    date,
  });

  // Filter data to only show selected district if in detail view
  const filteredData = data
    ? {
      ...(data as any),
      features: selectedDistrictId
        ? (data as any).features.filter((f: any) => f.properties.district_id === selectedDistrictId)
        : (data as any).features,
    }
    : null;

  // Dynamic styling based on AQI values
  const districtFillStyle = {
    type: 'fill' as const,
    paint: {
      'fill-color': [
        'case',
        ['<=', ['get', 'mean_aqi'], 50], '#22C55E', // Green - Good
        ['<=', ['get', 'mean_aqi'], 100], '#EAB308', // Yellow - Moderate
        ['<=', ['get', 'mean_aqi'], 150], '#F97316', // Orange - USG
        ['<=', ['get', 'mean_aqi'], 200], '#EF4444', // Red - Unhealthy
        ['<=', ['get', 'mean_aqi'], 300], '#8B1E23', // Dark Red - Very Unhealthy
        '#7E0023', // Maroon - Hazardous
      ],
      'fill-opacity': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        0.9, // Highlight on hover
        0.6, // Default
      ],
    },
  };

  const districtOutlineStyle = {
    type: 'line' as const,
    paint: {
      'line-color': '#ffffff',
      'line-width': 1,
      'line-opacity': 0.3,
    },
  };

  const districtLabelStyle = {
    type: 'symbol' as const,
    layout: {
      'text-field': ['get', 'district_name'],
      'text-size': 10,
      'text-offset': [0, 0],
      'text-anchor': 'center',
    } as any,
    paint: {
      'text-color': '#ffffff',
      'text-opacity': 0.7,
      'text-halo-color': '#000000',
      'text-halo-width': 1,
    },
  };

  // Development logging
  if (import.meta.env.DEV) {
    if (isLoading) {
      console.debug('[DistrictsLayer] Loading district exposure data...');
    }
    if (isError) {
      console.error('[DistrictsLayer] Error:', error);
    }
    if (data) {
      console.debug(`[DistrictsLayer] Loaded ${data.features?.length ?? 0} districts with PM2.5/AQI data`);
    }
  }

  return (
    <>
      {/* District fill - AQI choropleth */}
      <GeoJSONLayer
        id="districts"
        data={filteredData as any ?? null}
        visible={true}
        layerStyle={districtFillStyle as any}
      />

      {/* District outline */}
      <GeoJSONLayer
        id="districts-outline"
        data={filteredData as any ?? null}
        visible={true}
        layerStyle={districtOutlineStyle as any}
      />

      {/* District labels */}
      <GeoJSONLayer
        id="districts-labels"
        data={filteredData as any ?? null}
        visible={true}
        layerStyle={districtLabelStyle as any}
      />

      {/* Click handler on fill layer */}
      <GeoJSONLayer
        id="districts-click-handler"
        data={filteredData as any ?? null}
        visible={false}
        layerStyle={{ type: 'fill', paint: { 'fill-opacity': 0 } } as any}
        onFeatureClick={(feature) => {
          onDistrictClick?.(feature.properties as DistrictExposureProperties);
        }}
      />
    </>
  );
}

export default DistrictsLayer;
