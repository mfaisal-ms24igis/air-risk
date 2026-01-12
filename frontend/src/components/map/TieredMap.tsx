/**
 * TieredMap Component
 * 
 * Map component that renders different features based on user subscription tier.
 * - BASIC: Simplified geometry, 10 station limit, no tile layers
 * - PREMIUM: Full geometry, 50 station limit, raster tile layers, AI insights
 * 
 * @module components/map/TieredMap
 */

import { useEffect, useRef, useState } from 'react';
import maplibregl, { Map as MapLibreMap, LngLatBoundsLike } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useIsPremium, useTier } from '@/store';

// =============================================================================
// Types
// =============================================================================

interface TieredMapProps {
  onMapLoad?: (map: MapLibreMap) => void;
  onDistrictClick?: (districtId: number) => void;
  className?: string;
  style?: React.CSSProperties;
}

// =============================================================================
// Constants
// =============================================================================

const PAKISTAN_BOUNDS: LngLatBoundsLike = [
  [60.87, 23.69], // Southwest
  [77.84, 37.08], // Northeast
];

const INITIAL_VIEW = {
  center: [69.3451, 30.3753] as [number, number], // Pakistan center
  zoom: 5,
};

// =============================================================================
// Component
// =============================================================================

export function TieredMap({ onMapLoad, onDistrictClick, className, style }: TieredMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  
  const isPremium = useIsPremium();
  const tier = useTier();

  // =============================================================================
  // Initialize Map
  // =============================================================================

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const mapInstance = new MapLibreMap({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© CARTO © OpenStreetMap',
          },
        },
        layers: [
          {
            id: 'osm-tiles',
            type: 'raster',
            source: 'osm',
          },
        ],
      },
      center: INITIAL_VIEW.center,
      zoom: INITIAL_VIEW.zoom,
      maxBounds: PAKISTAN_BOUNDS,
      minZoom: 4,
      maxZoom: isPremium ? 18 : 14, // Premium gets higher zoom
    });

    // Add controls
    mapInstance.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapInstance.addControl(new maplibregl.ScaleControl(), 'bottom-left');

    // Add tier badge
    const tierBadge = document.createElement('div');
    tierBadge.className = 'maplibregl-ctrl maplibregl-ctrl-group';
    tierBadge.style.cssText = `
      background: ${isPremium ? '#10b981' : '#6b7280'};
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      pointer-events: none;
    `;
    tierBadge.textContent = tier;
    mapInstance.getContainer().appendChild(tierBadge);
    tierBadge.style.position = 'absolute';
    tierBadge.style.top = '10px';
    tierBadge.style.left = '10px';

    mapInstance.on('load', () => {
      setIsLoaded(true);
      onMapLoad?.(mapInstance);
    });

    map.current = mapInstance;

    return () => {
      mapInstance.remove();
      map.current = null;
    };
  }, [isPremium, tier, onMapLoad]);

  // =============================================================================
  // Load District Layer
  // =============================================================================

  useEffect(() => {
    if (!map.current || !isLoaded) return;

    const mapInstance = map.current;
    const accessToken = localStorage.getItem('auth-storage')
      ? JSON.parse(localStorage.getItem('auth-storage')!).state?.accessToken
      : null;

    if (!accessToken) return;

    // Fetch districts with tier-appropriate detail
    fetch('/api/v1/air-quality/spatial/districts/', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        // Add source
        if (!mapInstance.getSource('districts')) {
          mapInstance.addSource('districts', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: data.features || [],
            },
          });

          // Add fill layer
          mapInstance.addLayer({
            id: 'districts-fill',
            type: 'fill',
            source: 'districts',
            paint: {
              'fill-color': [
                'case',
                ['boolean', ['feature-state', 'hover'], false],
                '#3b82f6',
                '#e5e7eb',
              ],
              'fill-opacity': 0.3,
            },
          });

          // Add outline layer
          mapInstance.addLayer({
            id: 'districts-outline',
            type: 'line',
            source: 'districts',
            paint: {
              'line-color': '#6b7280',
              'line-width': isPremium ? 2 : 1,
            },
          });

          // Add labels (premium only for performance)
          if (isPremium) {
            mapInstance.addLayer({
              id: 'districts-labels',
              type: 'symbol',
              source: 'districts',
              layout: {
                'text-field': ['get', 'name'],
                'text-size': 12,
                'text-anchor': 'center',
              },
              paint: {
                'text-color': '#1f2937',
                'text-halo-color': '#ffffff',
                'text-halo-width': 1,
              },
            });
          }

          // Click handler
          mapInstance.on('click', 'districts-fill', (e) => {
            if (e.features && e.features[0]) {
              const districtId = e.features[0].properties?.id;
              if (districtId) {
                onDistrictClick?.(districtId);
              }
            }
          });

          // Hover cursor
          mapInstance.on('mouseenter', 'districts-fill', () => {
            mapInstance.getCanvas().style.cursor = 'pointer';
          });

          mapInstance.on('mouseleave', 'districts-fill', () => {
            mapInstance.getCanvas().style.cursor = '';
          });
        }
      })
      .catch((error) => {
        console.error('Failed to load districts:', error);
      });
  }, [isLoaded, isPremium, onDistrictClick]);

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="relative w-full h-full">
      <div
        ref={mapContainer}
        className={className || 'w-full h-full'}
        style={style}
      />
      
      {/* Tier upgrade prompt for basic users */}
      {!isPremium && (
        <div className="absolute bottom-20 left-1/2 transform -translate-x-1/2 bg-white shadow-lg rounded-lg p-4 max-w-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <svg className="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-gray-900">Upgrade to Premium</h3>
              <p className="mt-1 text-xs text-gray-600">
                Unlock high-resolution satellite tiles, AI-powered insights, and 50+ nearby stations
              </p>
              <button className="mt-2 text-xs font-medium text-blue-600 hover:text-blue-700">
                Learn more →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TieredMap;
