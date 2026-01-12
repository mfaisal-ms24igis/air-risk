/**
 * Example: Using Risk Map Layer in Your Map Component
 * 
 * This shows how to integrate the dynamic risk layer into
 * an existing MapLibre GL JS map.
 */

import { useRef, useEffect, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { RiskMapLayer, RiskLegend } from '@/components/RiskMapLayer';
import '@/components/RiskLegend.css';
import { useQuery } from '@tanstack/react-query';
import { getRiskTiles } from '@/services/risk';

export function AirQualityMap() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const [showRiskLayer, setShowRiskLayer] = useState(true);

  // Query for legend data
  const { data: riskData, isLoading } = useQuery({
    queryKey: ['risk-tiles', 7, 30],
    queryFn: () => getRiskTiles({ days: 7, sentinel_days_back: 30 }),
  });

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) return;

    const mapInstance = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [69.3451, 30.3753], // Pakistan center
      zoom: 5,
    });

    mapInstance.on('load', () => {
      setMap(mapInstance);
    });

    return () => {
      mapInstance.remove();
    };
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100vh' }}>
      {/* Map Container */}
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

      {/* Risk Layer (data-only component) */}
      <RiskMapLayer
        map={map}
        visible={showRiskLayer}
        days={7}
        sentinelDaysBack={30}
      />

      {/* Legend Overlay */}
      {showRiskLayer && (
        <RiskLegend
          legend={riskData?.legend || null}
          loading={isLoading}
          metadata={riskData?.metadata}
        />
      )}

      {/* Layer Toggle Control */}
      <div style={{
        position: 'absolute',
        top: 10,
        right: 10,
        background: 'white',
        padding: '10px',
        borderRadius: '4px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
        zIndex: 1000,
      }}>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={showRiskLayer}
            onChange={(e) => setShowRiskLayer(e.target.checked)}
            style={{ marginRight: '8px' }}
          />
          <span style={{ fontSize: '14px' }}>Risk Layer</span>
        </label>
      </div>

      {/* Status Indicator */}
      {riskData?.metadata && (
        <div style={{
          position: 'absolute',
          top: 10,
          left: 10,
          background: 'white',
          padding: '8px 12px',
          borderRadius: '4px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
          fontSize: '12px',
          zIndex: 1000,
        }}>
          <strong>Sentinel-5P:</strong>{' '}
          {new Date(riskData.metadata.sentinel5p_date).toLocaleDateString()}
          <br />
          <strong>Stations:</strong> {riskData.metadata.openaq_points}
          <br />
          <strong>Fusion:</strong>{' '}
          {(riskData.metadata.fusion_weights.ground * 100).toFixed(0)}% ground +{' '}
          {(riskData.metadata.fusion_weights.satellite * 100).toFixed(0)}% satellite
        </div>
      )}
    </div>
  );
}

export default AirQualityMap;
