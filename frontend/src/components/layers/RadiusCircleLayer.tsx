/**
 * Radius Circle Layer
 * 
 * Displays a circle around a location center (e.g., 5km radius)
 */

import { useEffect, useRef } from 'react';
import { useMap } from '@/contexts/MapContext';
import type maplibregl from 'maplibre-gl';

export interface RadiusCircleLayerProps {
  /** Center point [lng, lat] */
  center: [number, number] | null;
  /** Radius in kilometers */
  radiusKm?: number;
  /** Circle color */
  color?: string;
  /** Circle opacity */
  opacity?: number;
  /** Layer visibility */
  visible?: boolean;
}

/**
 * Create a GeoJSON circle polygon around a point
 */
function createCircle(
  center: [number, number],
  radiusKm: number = 5,
  steps: number = 64
): GeoJSON.Feature<GeoJSON.Polygon> {
  const [lng, lat] = center;
  const radiusInDegrees = radiusKm / 111.32; // Approximate conversion

  const coordinates: [number, number][] = [];
  for (let i = 0; i < steps; i++) {
    const angle = (i / steps) * Math.PI * 2;
    const x = lng + radiusInDegrees * Math.cos(angle);
    const y = lat + radiusInDegrees * Math.sin(angle);
    coordinates.push([x, y]);
  }
  coordinates.push(coordinates[0]); // Close the circle

  return {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [coordinates],
    },
    properties: {
      name: 'Exposure Radius',
      radiusKm,
    },
  };
}

export function RadiusCircleLayer({
  center,
  radiusKm = 5,
  color = '#0EA5E9',
  opacity = 0.2,
  visible = true,
}: RadiusCircleLayerProps) {
  const { map, isLoaded } = useMap();
  const sourceAddedRef = useRef(false);

  useEffect(() => {
    if (!map || !isLoaded || !center) return;

    const sourceId = 'radius-circle-source';
    const layerId = 'radius-circle-layer';

    const circleFeature = createCircle(center, radiusKm);
    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: [circleFeature],
    };

    try {
      // Add or update source
      const existingSource = map.getSource(sourceId);
      if (existingSource) {
        (existingSource as maplibregl.GeoJSONSource).setData(geojson);
      } else {
        map.addSource(sourceId, {
          type: 'geojson',
          data: geojson,
        });

        // Add fill layer
        map.addLayer({
          id: layerId,
          type: 'fill',
          source: sourceId,
          paint: {
            'fill-color': color,
            'fill-opacity': opacity,
          },
        });

        // Add outline layer
        map.addLayer({
          id: `${layerId}-outline`,
          type: 'line',
          source: sourceId,
          paint: {
            'line-color': color,
            'line-width': 2,
            'line-opacity': opacity * 2,
          },
        });

        sourceAddedRef.current = true;
      }
    } catch (e) {
      console.error('[RadiusCircleLayer] Error adding layer:', e);
    }

    return () => {
      if (!sourceAddedRef.current) return;

      try {
        const style = map.getStyle();
        if (!style) return;

        if (map.getLayer(layerId)) {
          map.removeLayer(layerId);
        }
        if (map.getLayer(`${layerId}-outline`)) {
          map.removeLayer(`${layerId}-outline`);
        }
        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }
      } catch (e) {
        // Ignore cleanup errors
      }

      sourceAddedRef.current = false;
    };
  }, [map, isLoaded, center, radiusKm, color, opacity]);

  // Handle visibility
  useEffect(() => {
    if (!map || !isLoaded) return;

    try {
      const layerId = 'radius-circle-layer';
      const outlineLayerId = `${layerId}-outline`;

      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
      }
      if (map.getLayer(outlineLayerId)) {
        map.setLayoutProperty(outlineLayerId, 'visibility', visible ? 'visible' : 'none');
      }
    } catch (e) {
      // Ignore errors
    }
  }, [map, isLoaded, visible]);

  return null; // This is a map layer, not a React component
}

export default RadiusCircleLayer;
