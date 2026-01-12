/**
 * Risk Map Layer Component
 * 
 * Displays dynamic pixel-wise air quality risk on MapLibre map
 * with automatic legend and status updates
 */

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getRiskTiles, getRiskStatus, type RiskLegend } from '@/services/risk';

interface RiskMapLayerProps {
  map: maplibregl.Map | null;
  visible?: boolean;
  days?: number;
  sentinelDaysBack?: number;
}

export function RiskMapLayer({
  map,
  visible = true,
  days = 7,
  sentinelDaysBack = 30,
}: RiskMapLayerProps) {
  const [, setLegend] = useState<RiskLegend | null>(null);

  // Fetch risk tiles
  const { data: riskData, refetch } = useQuery({
    queryKey: ['risk-tiles', days, sentinelDaysBack],
    queryFn: () => getRiskTiles({ days, sentinel_days_back: sentinelDaysBack }),
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 30, // 30 minutes
  });

  // Poll status every 5 minutes to check for new data
  const { data: statusData } = useQuery({
    queryKey: ['risk-status'],
    queryFn: getRiskStatus,
    refetchInterval: 1000 * 60 * 5, // 5 minutes
    refetchOnWindowFocus: true,
  });

  // Check if new data is available and refetch
  useEffect(() => {
    if (statusData?.status?.is_new) {
      console.log('New Sentinel-5P image detected, refreshing tiles...');
      refetch();
    }
  }, [statusData, refetch]);

  // Add/update map layer
  useEffect(() => {
    if (!map || !riskData?.success) return;

    const sourceId = 'risk-tiles';
    const layerId = 'risk-raster';

    // Remove existing layer and source
    if (map.getLayer(layerId)) {
      map.removeLayer(layerId);
    }
    if (map.getSource(sourceId)) {
      map.removeSource(sourceId);
    }

    // Add source
    map.addSource(sourceId, {
      type: 'raster',
      tiles: [riskData.tile_url],
      tileSize: 256,
    });

    // Add layer
    map.addLayer({
      id: layerId,
      type: 'raster',
      source: sourceId,
      paint: {
        'raster-opacity': visible ? 0.75 : 0,
      },
    });

    // Update legend
    setLegend(riskData.legend);

    console.log('Risk layer added:', {
      sentinel5p_date: riskData.metadata.sentinel5p_date,
      openaq_points: riskData.metadata.openaq_points,
    });

    return () => {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    };
  }, [map, riskData, visible]);

  // Handle visibility changes
  useEffect(() => {
    if (!map) return;

    const layerId = 'risk-raster';
    if (map.getLayer(layerId)) {
      map.setPaintProperty(layerId, 'raster-opacity', visible ? 0.75 : 0);
    }
  }, [map, visible]);

  return null; // This is a data-only component
}

interface RiskLegendProps {
  legend: RiskLegend | null;
  loading?: boolean;
  metadata?: any;
}

export function RiskLegend({ legend, loading, metadata }: RiskLegendProps) {
  if (loading) {
    return (
      <div className="risk-legend loading">
        <div className="legend-title">Loading risk data...</div>
      </div>
    );
  }

  if (!legend) return null;

  return (
    <div className="risk-legend">
      <div className="legend-header">
        <div className="legend-title">{legend.title}</div>
        <div className="legend-subtitle">{legend.subtitle}</div>
      </div>

      <div className="legend-gradient">
        {legend.stops.map((stop, index) => (
          <div
            key={index}
            className="legend-stop"
            style={{ backgroundColor: stop.color }}
            title={`${stop.label}: ${stop.value.toFixed(1)} ${legend.unit}`}
          />
        ))}
      </div>

      <div className="legend-labels">
        <span className="legend-label-min">
          {legend.min.toFixed(1)}
        </span>
        <span className="legend-label-max">
          {legend.max.toFixed(1)}
        </span>
      </div>

      {metadata && (
        <div className="legend-metadata">
          <small>
            Data: {new Date(metadata.sentinel5p_date).toLocaleDateString()} •{' '}
            {metadata.openaq_points} stations
          </small>
        </div>
      )}
    </div>
  );
}
