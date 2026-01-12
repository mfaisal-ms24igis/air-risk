/**
 * DashboardMap Component
 * 
 * Main map component that integrates MapBase with data layers.
 * Demonstrates the modular layer architecture with TanStack Query.
 * Now uses exposure API for PM2.5/AQI data visualization.
 * 
 * @module components/DashboardMap
 */

import { useState, useCallback } from 'react';
import { MapBase, MAP_STYLES } from '@/components/map';
import {
  DistrictsLayer,
  ProvincesLayer,
  type DistrictExposureProperties,
} from '@/components/layers';
import type { Map as MapLibreMap } from 'maplibre-gl';

// =============================================================================
// Types
// =============================================================================

export interface DashboardMapProps {
  /** Initial view mode */
  initialView?: 'provinces' | 'districts';
  /** Date filter for exposure data (YYYY-MM-DD) */
  date?: string;
  /** Color mode for districts - 'pm25' or 'aqi' */
  colorMode?: 'pm25' | 'aqi';
  /** Callback when map loads */
  onMapLoad?: (map: MapLibreMap) => void;
  /** Callback when district is selected */
  onDistrictSelect?: (district: DistrictExposureProperties) => void;
}

type ViewMode = 'provinces' | 'districts';

// =============================================================================
// Component
// =============================================================================

export function DashboardMap({
  initialView = 'provinces',
  date,
  colorMode = 'pm25',
  onMapLoad,
  onDistrictSelect,
}: DashboardMapProps) {
  // State
  const [viewMode, setViewMode] = useState<ViewMode>(initialView);
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);

  // Handle district click
  const handleDistrictClick = useCallback(
    (district: DistrictExposureProperties) => {
      console.log('[DashboardMap] District clicked:', district.district_name);
      onDistrictSelect?.(district);
    },
    [onDistrictSelect]
  );

  // Back to provinces view
  const handleBackToProvinces = useCallback(() => {
    setViewMode('provinces');
    setSelectedProvince(null);
  }, []);

  return (
    <div className="dashboard-map" style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Map with layers */}
      <MapBase
        style={MAP_STYLES.CARTO_LIGHT}
        center={[69.3451, 30.3753]}
        zoom={5}
        onLoad={onMapLoad}
        containerStyle={{ width: '100%', height: '100%' }}
      >
        {/* Provinces layer - visible in province view */}
        <ProvincesLayer />

        {/* Districts layer - visible when drilling down, uses exposure API */}
        <DistrictsLayer
          visible={viewMode === 'districts'}
          province={selectedProvince ?? undefined}
          date={date}
          colorMode={colorMode}
          onDistrictClick={handleDistrictClick}
        />
      </MapBase>

      {/* UI Controls Overlay */}
      <div className="map-controls" style={controlsStyle}>
        {/* View mode indicator & back button */}
        <div style={viewIndicatorStyle}>
          {viewMode === 'districts' && selectedProvince && (
            <>
              <button onClick={handleBackToProvinces} style={backButtonStyle}>
                ← Back to Provinces
              </button>
              <span style={{ marginLeft: '12px', fontWeight: 600 }}>
                {selectedProvince}
              </span>
            </>
          )}
          {viewMode === 'provinces' && (
            <span style={{ fontWeight: 600 }}>Select a Province</span>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="map-legend" style={legendStyle}>
        <h4 style={{ margin: '0 0 8px 0', fontSize: '12px' }}>PM2.5 (µg/m³)</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {LEGEND_ITEMS.map((item) => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '16px', height: '16px', backgroundColor: item.color, borderRadius: '2px' }} />
              <span style={{ fontSize: '11px' }}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================
// Legend Configuration
// ============================================

const LEGEND_ITEMS = [
  { color: '#00e400', label: '0-12 Good' },
  { color: '#ffff00', label: '12.1-35.4 Moderate' },
  { color: '#ff7e00', label: '35.5-55.4 USG' },
  { color: '#ff0000', label: '55.5-150.4 Unhealthy' },
  { color: '#8f3f97', label: '150.5-250.4 Very Unhealthy' },
  { color: '#7e0023', label: '250.5+ Hazardous' },
];

// ============================================
// Styles
// ============================================

const controlsStyle: React.CSSProperties = {
  position: 'absolute',
  top: '10px',
  left: '10px',
  zIndex: 1000,
};

const viewIndicatorStyle: React.CSSProperties = {
  backgroundColor: 'white',
  padding: '8px 16px',
  borderRadius: '4px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
  display: 'flex',
  alignItems: 'center',
};

const backButtonStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#0066cc',
  cursor: 'pointer',
  padding: '4px 8px',
  fontSize: '14px',
};

const legendStyle: React.CSSProperties = {
  position: 'absolute',
  bottom: '40px',
  right: '10px',
  backgroundColor: 'white',
  padding: '12px',
  borderRadius: '4px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
  zIndex: 1000,
};

export default DashboardMap;
