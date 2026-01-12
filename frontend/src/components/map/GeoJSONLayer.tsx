/**
 * GeoJSONLayer Component
 * Reusable component for adding GeoJSON data as map layers
 */

import { useEffect, useRef } from 'react';
import { useMap } from '@/contexts/MapContext';
import type {
  GeoJSONGeometry,
} from '@/types';
import type {
  FillLayerSpecification,
  LineLayerSpecification,
  CircleLayerSpecification,
  SymbolLayerSpecification,
} from 'maplibre-gl';

// ============================================
// Types
// ============================================

type LayerSpecification =
  | Omit<FillLayerSpecification, 'id' | 'source'>
  | Omit<LineLayerSpecification, 'id' | 'source'>
  | Omit<CircleLayerSpecification, 'id' | 'source'>
  | Omit<SymbolLayerSpecification, 'id' | 'source'>;

export interface GeoJSONLayerProps<P = any> {
  /** Unique identifier for the source and layer */
  id: string;
  /** GeoJSON data to display */
  data: any | null;
  /** Layer style specification (without id and source) - optional, defaults to simple fill */
  layerStyle?: LayerSpecification;
  /** Additional layers (e.g., outline for fill layers) */
  additionalLayers?: Array<LayerSpecification & { id: string }>;
  /** Insert layer before this layer ID */
  beforeId?: string;
  /** Callback when a feature is clicked */
  onFeatureClick?: (feature: GeoJSON.Feature<GeoJSONGeometry, P>, e: maplibregl.MapMouseEvent) => void;
  /** Callback when hovering over a feature */
  onFeatureHover?: (feature: GeoJSON.Feature<GeoJSONGeometry, P> | null, e: maplibregl.MapMouseEvent) => void;
  /** Whether layer is visible */
  visible?: boolean;
}

// ============================================
// Component
// ============================================

export function GeoJSONLayer<P extends Record<string, unknown>>({
  id,
  data,
  layerStyle,
  additionalLayers = [],
  beforeId,
  onFeatureClick,
  onFeatureHover,
  visible = true,
}: GeoJSONLayerProps<P>) {
  const { map, isLoaded } = useMap();
  const sourceAddedRef = useRef(false);
  const layersAddedRef = useRef<string[]>([]);

  // Add/update source and layers
  useEffect(() => {
    if (!map || !isLoaded || !data) return;

    const sourceId = `${id}-source`;
    const mainLayerId = `${id}-layer`;

    // Default layer style if not provided
    const defaultStyle: LayerSpecification = {
      type: 'fill',
      paint: {
        'fill-color': '#0EA5E9',
        'fill-opacity': 0.5,
      },
    };

    const finalLayerStyle = layerStyle || defaultStyle;

    // Safety check: ensure map methods are available
    if (!map.getSource || !map.addSource || !map.addLayer) {
      console.warn('[GeoJSONLayer] Map methods not ready yet');
      return;
    }

    // Check if source exists
    const existingSource = map.getSource(sourceId);

    if (existingSource) {
      // Update existing source data
      (existingSource as maplibregl.GeoJSONSource).setData(data as GeoJSON.FeatureCollection);
    } else {
      // Add new source
      map.addSource(sourceId, {
        type: 'geojson',
        data: data as GeoJSON.FeatureCollection,
      });
      sourceAddedRef.current = true;

      // Add main layer
      map.addLayer(
        {
          ...finalLayerStyle,
          id: mainLayerId,
          source: sourceId,
        } as maplibregl.LayerSpecification,
        beforeId
      );
      layersAddedRef.current.push(mainLayerId);

      // Add additional layers
      additionalLayers.forEach((layer, index) => {
        const additionalLayerId = layer.id || `${id}-layer-${index}`;
        map.addLayer(
          {
            ...layer,
            id: additionalLayerId,
            source: sourceId,
          } as maplibregl.LayerSpecification,
          beforeId
        );
        layersAddedRef.current.push(additionalLayerId);
      });
    }

    // Cleanup on unmount
    return () => {
      // Check if map still exists and has valid style (not destroyed)
      if (!map || !sourceAddedRef.current) return;
      
      try {
        // Check if map style is still valid before accessing layers
        const style = map.getStyle();
        if (!style) return;
        
        // Remove layers first
        layersAddedRef.current.forEach((layerId) => {
          try {
            if (map.getLayer(layerId)) {
              map.removeLayer(layerId);
            }
          } catch (e) {
            // Layer might already be removed or map destroyed
          }
        });
        // Then remove source
        try {
          if (map.getSource(sourceId)) {
            map.removeSource(sourceId);
          }
        } catch (e) {
          // Source might already be removed or map destroyed
        }
      } catch (e) {
        // Map might be in an invalid state, ignore cleanup errors
      }
      
      sourceAddedRef.current = false;
      layersAddedRef.current = [];
    };
  }, [map, isLoaded, id, data, layerStyle, additionalLayers, beforeId]);

  // Handle visibility
  useEffect(() => {
    if (!map || !isLoaded) return;
    
    try {
      const style = map.getStyle();
      if (!style) return;
      
      layersAddedRef.current.forEach((layerId) => {
        try {
          if (map.getLayer(layerId)) {
            map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
          }
        } catch (e) {
          // Ignore errors if map is in invalid state
        }
      });
    } catch (e) {
      // Map might be destroyed
    }
  }, [map, isLoaded, visible]);

  // Handle click events
  useEffect(() => {
    if (!map || !isLoaded || !onFeatureClick) return;

    const mainLayerId = `${id}-layer`;

    const handleClick = (e: maplibregl.MapMouseEvent) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [mainLayerId],
      });

      if (features.length > 0) {
        onFeatureClick(features[0] as unknown as GeoJSON.Feature<GeoJSONGeometry, P>, e);
      }
    };

    // Change cursor on hover
    const handleMouseEnter = () => {
      map.getCanvas().style.cursor = 'pointer';
    };

    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = '';
    };

    // Only add listeners if layer exists
    try {
      if (map.getLayer(mainLayerId)) {
        map.on('click', mainLayerId, handleClick);
        map.on('mouseenter', mainLayerId, handleMouseEnter);
        map.on('mouseleave', mainLayerId, handleMouseLeave);
      }
    } catch (e) {
      // Layer might not exist yet
    }

    return () => {
      try {
        map.off('click', mainLayerId, handleClick);
        map.off('mouseenter', mainLayerId, handleMouseEnter);
        map.off('mouseleave', mainLayerId, handleMouseLeave);
      } catch (e) {
        // Map might be destroyed
      }
    };
  }, [map, isLoaded, id, onFeatureClick]);

  // Handle hover events
  useEffect(() => {
    if (!map || !isLoaded || !onFeatureHover) return;

    const mainLayerId = `${id}-layer`;
    let hoveredFeatureId: string | number | null = null;

    const handleMouseMove = (e: maplibregl.MapMouseEvent) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [mainLayerId],
      });

      if (features.length > 0) {
        const feature = features[0] as unknown as GeoJSON.Feature<GeoJSONGeometry, P>;
        if (feature.id !== hoveredFeatureId) {
          hoveredFeatureId = feature.id ?? null;
          onFeatureHover(feature, e);
        }
      } else if (hoveredFeatureId !== null) {
        hoveredFeatureId = null;
        onFeatureHover(null, e);
      }
    };

    // Only add listener if layer exists
    try {
      if (map.getLayer(mainLayerId)) {
        map.on('mousemove', mainLayerId, handleMouseMove);
      }
    } catch (e) {
      // Layer might not exist yet
    }

    return () => {
      try {
        map.off('mousemove', mainLayerId, handleMouseMove);
      } catch (e) {
        // Map might be destroyed
      }
    };
  }, [map, isLoaded, id, onFeatureHover]);

  // This component doesn't render anything - it just manages map layers
  return null;
}

export default GeoJSONLayer;
