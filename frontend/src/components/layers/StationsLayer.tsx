/**
 * StationsLayer Component
 * 
 * Displays all air quality monitoring stations (~370+) as points on the map.
 * Supports clustering for performance and color-coding by latest AQI.
 * 
 * @module components/layers/StationsLayer
 */

import { useEffect, useCallback } from 'react';
import { useMap } from '@/contexts/MapContext';
import { useStationsGeoJSON } from '@/hooks/queries';
import type { StationProperties } from '@/types/models';

// =============================================================================
// Types
// =============================================================================

export interface StationsLayerProps {
  /** Whether the layer is visible */
  visible?: boolean;
  /** Enable clustering for many stations */
  clustered?: boolean;
  /** Callback when a station is clicked */
  onStationClick?: (station: StationProperties) => void;
}

// =============================================================================
// Constants
// =============================================================================

const SOURCE_ID = 'stations-source';
const LAYER_ID = 'stations-layer';
const CLUSTER_LAYER_ID = 'stations-clusters';
const UNCLUSTERED_LAYER_ID = 'stations-unclustered';

// AQI-based color for station points
const getStationColor = () => [
  'case',
  ['has', 'pm25'],
  [
    'step',
    ['get', 'pm25'],
    '#00e400',       // 0-12: Good - Green
    12.1, '#ffff00', // 12.1-35.4: Moderate - Yellow
    35.5, '#ff7e00', // 35.5-55.4: USG - Orange
    55.5, '#ff0000', // 55.5-150.4: Unhealthy - Red
    150.5, '#8f3f97',// 150.5-250.4: Very Unhealthy - Purple
    250.5, '#7e0023',// 250.5+: Hazardous - Maroon
  ],
  '#3b82f6', // Default blue if no PM2.5 data
];

// Color based on active status
const getActiveColor = () => [
  'case',
  ['get', 'is_active'],
  '#3b82f6', // Active - Blue
  '#9ca3af', // Inactive - Gray
];

// =============================================================================
// Component
// =============================================================================

export function StationsLayer({
  visible = true,
  clustered = true,
  onStationClick,
}: StationsLayerProps) {
  const { map, isLoaded } = useMap();
  const { data: stationsGeoJSON } = useStationsGeoJSON();

  // Add source and layers
  useEffect(() => {
    if (!map || !isLoaded || !stationsGeoJSON) return;

    // Remove existing layers/source if they exist
    try {
      if (map.getLayer(UNCLUSTERED_LAYER_ID)) map.removeLayer(UNCLUSTERED_LAYER_ID);
      if (map.getLayer(CLUSTER_LAYER_ID)) map.removeLayer(CLUSTER_LAYER_ID);
      if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
    } catch (e) {
      // Layers might not exist yet
    }

    // Add source with clustering option
    map.addSource(SOURCE_ID, {
      type: 'geojson',
      data: stationsGeoJSON,
      cluster: clustered,
      clusterMaxZoom: 12,
      clusterRadius: 50,
    });

    if (clustered) {
      // Cluster circles
      map.addLayer({
        id: CLUSTER_LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': [
            'step',
            ['get', 'point_count'],
            '#51bbd6',   // < 10 stations
            10, '#f1f075', // 10-50 stations
            50, '#f28cb1', // 50+ stations
          ],
          'circle-radius': [
            'step',
            ['get', 'point_count'],
            15,   // < 10: 15px
            10, 20, // 10-50: 20px
            50, 25, // 50+: 25px
          ],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
        },
        layout: {
          visibility: visible ? 'visible' : 'none',
        },
      });

      // Cluster count labels - removed due to missing glyphs in style
      // Users can still see cluster size by the circle size

      // Unclustered individual stations
      map.addLayer({
        id: UNCLUSTERED_LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': [
            'case',
            ['has', 'pm25'],
            getStationColor(),
            getActiveColor()
          ] as any,
          'circle-radius': 8,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
        },
        layout: {
          visibility: visible ? 'visible' : 'none',
        },
      });
    } else {
      // Non-clustered: simple circles
      map.addLayer({
        id: LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        paint: {
          'circle-color': [
            'case',
            ['!', ['get', 'is_active']], '#9ca3af', // Inactive -> Gray (Priority 1)
            ['has', 'pm25'], getStationColor(),     // Active + Data -> AQI Color
            '#3b82f6'                               // Active + No Data -> Blue
          ] as any,
          'circle-radius': [
            'case',
            ['!', ['get', 'is_active']], 4,  // Inactive -> Smaller
            8                                // Active -> Normal
          ] as any,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
        },
        layout: {
          visibility: visible ? 'visible' : 'none',
        },
      });
    }

    // Cleanup
    return () => {
      if (!map) return;
      try {
        const style = map.getStyle();
        if (!style) return;

        if (map.getLayer(UNCLUSTERED_LAYER_ID)) map.removeLayer(UNCLUSTERED_LAYER_ID);
        if (map.getLayer(CLUSTER_LAYER_ID)) map.removeLayer(CLUSTER_LAYER_ID);
        if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
        if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      } catch (e) {
        // Map might be destroyed already
      }
    };
  }, [map, isLoaded, stationsGeoJSON, clustered, visible]);

  // Update visibility when prop changes
  useEffect(() => {
    if (!map || !isLoaded) return;

    const layerIds = clustered
      ? [CLUSTER_LAYER_ID, UNCLUSTERED_LAYER_ID]
      : [LAYER_ID];

    layerIds.forEach(layerId => {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
      }
    });
  }, [map, isLoaded, visible, clustered]);

  // Handle click events
  const handleClick = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      if (!map || !onStationClick) return;

      const clickLayerId = clustered ? UNCLUSTERED_LAYER_ID : LAYER_ID;
      const features = map.queryRenderedFeatures(e.point, { layers: [clickLayerId] });

      if (features.length > 0) {
        const feature = features[0];
        onStationClick(feature.properties as StationProperties);
      }
    },
    [map, onStationClick, clustered]
  );

  // Handle cluster click (zoom in)
  const handleClusterClick = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      if (!map || !clustered) return;

      const features = map.queryRenderedFeatures(e.point, { layers: [CLUSTER_LAYER_ID] });
      if (features.length === 0) return;

      const clusterId = features[0].properties?.cluster_id;
      const source = map.getSource(SOURCE_ID) as any;

      source.getClusterExpansionZoom(clusterId, (err: any, zoom: number) => {
        if (err || zoom === undefined) return;
        const geometry = features[0].geometry;
        if (geometry.type === 'Point') {
          map.easeTo({
            center: geometry.coordinates as [number, number],
            zoom: zoom,
          });
        }
      });
    },
    [map, clustered]
  );

  // Attach click handlers
  useEffect(() => {
    if (!map || !isLoaded) return;

    // Safety check: ensure map methods are available
    if (!map.getLayer || !map.on || !map.off) {
      console.warn('[StationsLayer] Map methods not ready yet');
      return;
    }

    const clickLayerId = clustered ? UNCLUSTERED_LAYER_ID : LAYER_ID;

    if (onStationClick && map.getLayer(clickLayerId)) {
      map.on('click', clickLayerId, handleClick);
    }

    if (clustered && map.getLayer(CLUSTER_LAYER_ID)) {
      map.on('click', CLUSTER_LAYER_ID, handleClusterClick);
    }

    // Cursor changes
    const layersToWatch = clustered
      ? [CLUSTER_LAYER_ID, UNCLUSTERED_LAYER_ID]
      : [LAYER_ID];

    layersToWatch.forEach(layerId => {
      if (map.getLayer(layerId)) {
        map.on('mouseenter', layerId, () => {
          map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', layerId, () => {
          map.getCanvas().style.cursor = '';
        });
      }
    });

    return () => {
      if (!map) return;
      try {
        if (map.getLayer(clickLayerId)) {
          map.off('click', clickLayerId, handleClick);
        }
        if (clustered && map.getLayer(CLUSTER_LAYER_ID)) {
          map.off('click', CLUSTER_LAYER_ID, handleClusterClick);
        }
      } catch (e) {
        // Ignore cleanup errors
      }
    };
  }, [map, isLoaded, onStationClick, handleClick, handleClusterClick, clustered]);

  // This component doesn't render any DOM directly
  return null;
}

export default StationsLayer;
