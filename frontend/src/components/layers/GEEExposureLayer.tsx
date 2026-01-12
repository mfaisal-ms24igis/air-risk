/**
 * GEE Exposure Layer Component
 * 
 * Displays pixel-wise exposure tiles from Google Earth Engine
 * calculation results. Premium feature only.
 */

import { useEffect, useState, useCallback } from 'react';
import { useMap } from '@/contexts/MapContext';
import type { GEEExposureResult } from '@/api/geeExposure';
import type { RasterSource } from 'maplibre-gl';

export interface GEEExposureLayerProps {
  /** Exposure result with tile URLs */
  exposureResult: GEEExposureResult | null;
  /** Show exposure or AQI tiles */
  mode: 'exposure' | 'aqi';
  /** Layer visibility */
  visible?: boolean;
  /** Opacity (0-1) */
  opacity?: number;
  /** Layer ID prefix */
  layerId?: string;
}

export function GEEExposureLayer({
  exposureResult,
  mode = 'exposure',
  visible = true,
  opacity = 0.7,
  layerId = 'gee-exposure',
}: GEEExposureLayerProps) {
  const { map } = useMap();
  const [isAdded, setIsAdded] = useState(false);

  const sourceId = `${layerId}-source`;
  const rasterLayerId = `${layerId}-layer`;

  // Get tile URL based on mode
  const tileUrl = mode === 'exposure' 
    ? exposureResult?.exposure_tile_url 
    : exposureResult?.aqi_tile_url;

  // Add/update layer when map is ready and result changes
  useEffect(() => {
    if (!map || !exposureResult || !tileUrl) {
      return;
    }

    const addLayer = () => {
      try {
        // Remove existing layer and source if present
        if (map.getLayer(rasterLayerId)) {
          map.removeLayer(rasterLayerId);
        }
        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }

        // Add raster source with GEE tile URL
        map.addSource(sourceId, {
          type: 'raster',
          tiles: [tileUrl],
          tileSize: 256,
          attribution: 'Google Earth Engine',
        } as RasterSource);

        // Add raster layer
        map.addLayer({
          id: rasterLayerId,
          type: 'raster',
          source: sourceId,
          paint: {
            'raster-opacity': visible ? opacity : 0,
            'raster-fade-duration': 300,
          },
        });

        setIsAdded(true);
        console.log(`[GEEExposureLayer] Added ${mode} layer for district ${exposureResult.district_name}`);
      } catch (error) {
        console.error('[GEEExposureLayer] Error adding layer:', error);
      }
    };

    if (map.isStyleLoaded()) {
      addLayer();
    } else {
      map.once('load', addLayer);
    }

    // Cleanup on unmount or when result changes
    return () => {
      if (map.getLayer(rasterLayerId)) {
        map.removeLayer(rasterLayerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
      setIsAdded(false);
    };
  }, [map, exposureResult, tileUrl, mode, sourceId, rasterLayerId]);

  // Update visibility
  useEffect(() => {
    if (!map || !isAdded) return;

    try {
      if (map.getLayer(rasterLayerId)) {
        map.setLayoutProperty(
          rasterLayerId,
          'visibility',
          visible ? 'visible' : 'none'
        );
      }
    } catch (error) {
      console.error('[GEEExposureLayer] Error updating visibility:', error);
    }
  }, [map, isAdded, visible, rasterLayerId]);

  // Update opacity
  useEffect(() => {
    if (!map || !isAdded || !visible) return;

    try {
      if (map.getLayer(rasterLayerId)) {
        map.setPaintProperty(rasterLayerId, 'raster-opacity', opacity);
      }
    } catch (error) {
      console.error('[GEEExposureLayer] Error updating opacity:', error);
    }
  }, [map, isAdded, visible, opacity, rasterLayerId]);

  return null; // This is a map layer component, no DOM rendering
}

export default GEEExposureLayer;
