/**
 * Map Context
 * 
 * Provides MapLibre map instance to child components with:
 * - Type-safe map access
 * - Navigation methods (flyTo, fitBounds)
 * - Layer management utilities
 * - Event subscription helpers
 * 
 * @module contexts/MapContext
 */

import { createContext, useContext, useEffect } from 'react';
import type {
  Map as MapLibreMap,
  LngLatLike,
  LngLatBoundsLike,
  FlyToOptions,
  FitBoundsOptions,
  MapMouseEvent,
  MapLayerMouseEvent,
} from 'maplibre-gl';
import type { BBox } from 'geojson';

// =============================================================================
// Types
// =============================================================================

/**
 * Map navigation options
 */
export interface MapNavigationOptions {
  /** Animation duration in ms (0 = instant) */
  duration?: number;
  /** Easing function */
  easing?: (t: number) => number;
  /** Padding around the target */
  padding?: number | { top: number; bottom: number; left: number; right: number };
  /** Maximum zoom level */
  maxZoom?: number;
}

/**
 * Map context value with all available operations
 */
export interface MapContextValue {
  /** The MapLibre map instance (null until loaded) */
  map: MapLibreMap | null;
  
  /** Whether the map has finished loading */
  isLoaded: boolean;
  
  // -------------------------------------------------------------------------
  // Navigation Methods
  // -------------------------------------------------------------------------
  
  /**
   * Fly to a specific location
   * @param center - Target center coordinates [lng, lat]
   * @param zoom - Target zoom level
   * @param options - Animation options
   */
  flyTo: (
    center: LngLatLike,
    zoom?: number,
    options?: MapNavigationOptions
  ) => void;
  
  /**
   * Fit the map to bounds
   * @param bounds - Bounding box [west, south, east, north] or LngLatBounds
   * @param options - Fit options
   */
  fitBounds: (
    bounds: LngLatBoundsLike | BBox,
    options?: MapNavigationOptions
  ) => void;
  
  /**
   * Reset to initial view
   */
  resetView: () => void;
  
  // -------------------------------------------------------------------------
  // Layer Utilities
  // -------------------------------------------------------------------------
  
  /**
   * Set a filter on a layer
   * @param layerId - The layer ID
   * @param filter - MapLibre filter expression
   */
  setLayerFilter: (layerId: string, filter: unknown[] | null) => void;
  
  /**
   * Set layer visibility
   * @param layerId - The layer ID
   * @param visible - Whether layer should be visible
   */
  setLayerVisibility: (layerId: string, visible: boolean) => void;
  
  /**
   * Set a paint property on a layer
   * @param layerId - The layer ID
   * @param property - Paint property name
   * @param value - Property value
   */
  setLayerPaint: (layerId: string, property: string, value: unknown) => void;
}

// =============================================================================
// Default Values
// =============================================================================

const DEFAULT_CENTER: LngLatLike = [69.3451, 30.3753]; // Pakistan
const DEFAULT_ZOOM = 5;

const noop = () => {
  if (import.meta.env.DEV) {
    console.warn('[MapContext] Method called before map initialization');
  }
};

const defaultContextValue: MapContextValue = {
  map: null,
  isLoaded: false,
  flyTo: noop,
  fitBounds: noop,
  resetView: noop,
  setLayerFilter: noop,
  setLayerVisibility: noop,
  setLayerPaint: noop,
};

// =============================================================================
// Context
// =============================================================================

export const MapContext = createContext<MapContextValue>(defaultContextValue);
MapContext.displayName = 'MapContext';

// =============================================================================
// Hooks
// =============================================================================

/**
 * Access the map context
 * 
 * @throws Error if used outside MapProvider
 * @returns Map context value with all methods
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { map, isLoaded, flyTo } = useMap();
 *   
 *   const handleClick = () => {
 *     flyTo([74.3587, 31.5204], 12); // Fly to Lahore
 *   };
 *   
 *   return <button onClick={handleClick}>Go to Lahore</button>;
 * }
 * ```
 */
export function useMap(): MapContextValue {
  const context = useContext(MapContext);
  
  if (context === undefined) {
    throw new Error('useMap must be used within a MapProvider (MapBase component)');
  }
  
  return context;
}

/**
 * Get map instance only when loaded
 * Returns null if map is not ready
 * 
 * @returns Map instance or null
 */
export function useMapWhenReady(): MapLibreMap | null {
  const { map, isLoaded } = useMap();
  return isLoaded ? map : null;
}

/**
 * Subscribe to map events with automatic cleanup
 * 
 * @param eventType - Map event type
 * @param handler - Event handler
 * @param layerId - Optional layer ID for layer-specific events
 * 
 * @example
 * ```tsx
 * useMapEvent('click', (e) => console.log('Clicked at', e.lngLat));
 * useMapEvent('click', (e) => console.log('District clicked'), 'districts-layer');
 * ```
 */
export function useMapEvent(
  eventType: string,
  handler: (e: MapMouseEvent | MapLayerMouseEvent) => void,
  layerId?: string
): void {
  const { map, isLoaded } = useMap();
  
  // FIX: Changed from useCallback to useEffect
  useEffect(() => {
    if (!map || !isLoaded) return;
    
    if (layerId) {
      map.on(eventType as 'click', layerId, handler as (e: MapLayerMouseEvent) => void);
    } else {
      map.on(eventType as 'click', handler as (e: MapMouseEvent) => void);
    }
    
    return () => {
      if (layerId) {
        map.off(eventType as 'click', layerId, handler as (e: MapLayerMouseEvent) => void);
      } else {
        map.off(eventType as 'click', handler as (e: MapMouseEvent) => void);
      }
    };
  }, [map, isLoaded, eventType, handler, layerId]);
}

// =============================================================================
// Context Value Factory
// =============================================================================

/**
 * Create map context value from a map instance
 * Used internally by MapBase component
 * 
 * @param map - MapLibre map instance
 * @param isLoaded - Whether map is loaded
 * @returns Complete context value
 */
export function createMapContextValue(
  map: MapLibreMap | null,
  isLoaded: boolean
): MapContextValue {
  // Navigation methods
  const flyTo = (
    center: LngLatLike,
    zoom?: number,
    options?: MapNavigationOptions
  ) => {
    if (!map) return;
    
    const flyOptions: FlyToOptions = {
      center,
      duration: options?.duration ?? 1500,
      essential: true,
    };
    
    if (zoom !== undefined) {
      flyOptions.zoom = zoom;
    }
    
    if (options?.padding !== undefined) {
      flyOptions.padding = options.padding;
    }
    
    // Note: maxZoom is set via zoom parameter, not as separate property
    if (options?.maxZoom !== undefined && zoom === undefined) {
      flyOptions.zoom = Math.min(map.getZoom(), options.maxZoom);
    }
    
    map.flyTo(flyOptions);
  };
  
  const fitBounds = (
    bounds: LngLatBoundsLike | BBox,
    options?: MapNavigationOptions
  ) => {
    if (!map) return;
    
    // Convert GeoJSON BBox to LngLatBoundsLike if needed
    const lngLatBounds: LngLatBoundsLike = Array.isArray(bounds) && bounds.length === 4
      ? [[bounds[0], bounds[1]], [bounds[2], bounds[3]]]
      : bounds as LngLatBoundsLike;
    
    const fitOptions: FitBoundsOptions = {
      duration: options?.duration ?? 1500,
      padding: options?.padding ?? 50,
      maxZoom: options?.maxZoom ?? 14,
    };
    
    map.fitBounds(lngLatBounds, fitOptions);
  };
  
  const resetView = () => {
    if (!map) return;
    map.flyTo({
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      duration: 1500,
    });
  };
  
  // Layer utilities
  const setLayerFilter = (layerId: string, filter: unknown[] | null) => {
    if (!map || !map.getLayer(layerId)) return;
    map.setFilter(layerId, filter as maplibregl.FilterSpecification);
  };
  
  const setLayerVisibility = (layerId: string, visible: boolean) => {
    if (!map || !map.getLayer(layerId)) return;
    map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
  };
  
  const setLayerPaint = (layerId: string, property: string, value: unknown) => {
    if (!map || !map.getLayer(layerId)) return;
    map.setPaintProperty(layerId, property, value);
  };
  
  return {
    map,
    isLoaded,
    flyTo,
    fitBounds,
    resetView,
    setLayerFilter,
    setLayerVisibility,
    setLayerPaint,
  };
}

export default MapContext;
