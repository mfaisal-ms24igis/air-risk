/**
 * MapBase Component
 * 
 * Core map component that initializes MapLibre and provides context to children.
 * Handles React 18 StrictMode double-mount correctly.
 * 
 * Features:
 * - Native MapLibre GL JS (no wrappers)
 * - React 18 StrictMode safe
 * - Context-based map instance sharing
 * - Pre-configured base map styles
 * 
 * @module components/map/MapBase
 */

import {
  useRef,
  useEffect,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
  type CSSProperties,
} from 'react';
import maplibregl, { Map as MapLibreMap, NavigationControl, ScaleControl } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MapContext, createMapContextValue } from '@/contexts/MapContext';

// ============================================
// Map Style Options
// ============================================

export const MAP_STYLES = {
  // OpenStreetMap Raster
  OSM: {
    version: 8 as const,
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      osm: {
        type: 'raster' as const,
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors',
      },
    },
    layers: [
      {
        id: 'osm-tiles',
        type: 'raster' as const,
        source: 'osm',
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  },
  
  // Carto Light (Vector-like appearance)
  CARTO_LIGHT: {
    version: 8 as const,
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      carto: {
        type: 'raster' as const,
        tiles: [
          'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
          'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
          'https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        ],
        tileSize: 256,
        attribution: '© CARTO © OpenStreetMap contributors',
      },
    },
    layers: [
      {
        id: 'carto-tiles',
        type: 'raster' as const,
        source: 'carto',
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  },
  
  // Carto Dark
  CARTO_DARK: {
    version: 8 as const,
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      carto: {
        type: 'raster' as const,
        tiles: [
          'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        ],
        tileSize: 256,
        attribution: '© CARTO © OpenStreetMap contributors',
      },
    },
    layers: [
      {
        id: 'carto-tiles',
        type: 'raster' as const,
        source: 'carto',
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  },
  
  // Satellite Imagery
  SATELLITE: {
    version: 8 as const,
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      satellite: {
        type: 'raster' as const,
        tiles: [
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        ],
        tileSize: 256,
        attribution: '© Esri, Maxar, Earthstar Geographics',
      },
    },
    layers: [
      {
        id: 'satellite-tiles',
        type: 'raster' as const,
        source: 'satellite',
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  },
} as const;

// ============================================
// Component Props
// ============================================

export interface MapBaseProps {
  /** Child components (layers, controls, etc.) */
  children?: ReactNode;
  /** Initial center [lng, lat] */
  center?: [number, number];
  /** Initial zoom level */
  zoom?: number;
  /** Min zoom level */
  minZoom?: number;
  /** Max zoom level */
  maxZoom?: number;
  /** Map style - use MAP_STYLES or custom style object */
  style?: typeof MAP_STYLES[keyof typeof MAP_STYLES] | maplibregl.StyleSpecification;
  /** Container style */
  containerStyle?: CSSProperties;
  /** Container className */
  className?: string;
  /** Show navigation controls */
  showNavigation?: boolean;
  /** Show scale control */
  showScale?: boolean;
  /** Callback when map loads */
  onLoad?: (map: MapLibreMap) => void;
  /** Callback on map click */
  onClick?: (e: maplibregl.MapMouseEvent) => void;
}

// Default props
const DEFAULT_CENTER: [number, number] = [69.3451, 30.3753]; // Pakistan center
const DEFAULT_ZOOM = 5;

// ============================================
// MapBase Component
// ============================================

export function MapBase({
  children,
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  minZoom = 3,
  maxZoom = 18,
  style = MAP_STYLES.CARTO_LIGHT,
  containerStyle,
  className = '',
  showNavigation = true,
  showScale = true,
  onLoad,
  onClick,
}: MapBaseProps) {
  // Refs
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  
  // State
  const [isLoaded, setIsLoaded] = useState(false);
  const [map, setMap] = useState<MapLibreMap | null>(null);

  // Initialize map - handles React 18 strict mode double-fire
  useEffect(() => {
    // Skip if already initialized or container not ready
    if (mapRef.current || !mapContainerRef.current) return;

    // Create map instance
    const mapInstance = new maplibregl.Map({
      container: mapContainerRef.current,
      style: style as maplibregl.StyleSpecification,
      center,
      zoom,
      minZoom,
      maxZoom,
      attributionControl: false, // We'll add it manually for better control
    });

    // Store in ref immediately to prevent double initialization
    mapRef.current = mapInstance;

    // Add controls
    if (showNavigation) {
      mapInstance.addControl(new NavigationControl(), 'top-right');
    }
    
    if (showScale) {
      mapInstance.addControl(
        new ScaleControl({ maxWidth: 100, unit: 'metric' }),
        'bottom-left'
      );
    }

    // Handle load event
    mapInstance.on('load', () => {
      setMap(mapInstance);
      setIsLoaded(true);
      onLoad?.(mapInstance);
    });

    // Cleanup on unmount
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        setMap(null);
        setIsLoaded(false);
      }
    };
    // Only run on mount - ignore dependency warnings for initialization
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle click events
  const handleClick = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      onClick?.(e);
    },
    [onClick]
  );

  useEffect(() => {
    if (!map || !onClick) return;
    
    map.on('click', handleClick);
    
    return () => {
      map.off('click', handleClick);
    };
  }, [map, onClick, handleClick]);

  // Create context value with all navigation methods
  const contextValue = useMemo(
    () => createMapContextValue(map, isLoaded),
    [map, isLoaded]
  );

  return (
    <MapContext.Provider value={contextValue}>
      <div
        ref={mapContainerRef}
        className={`map-container w-full h-full min-h-[400px] ${className}`}
        style={containerStyle}
      />
      {/* Render children only when map is loaded */}
      {isLoaded && children}
    </MapContext.Provider>
  );
}

export default MapBase;
