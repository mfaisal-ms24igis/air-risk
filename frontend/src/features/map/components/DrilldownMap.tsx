import { useEffect, useRef, useState } from 'react';
import maplibregl, { Map as MapLibreMap, LngLatBoundsLike } from 'maplibre-gl';
import { MapPin, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import 'maplibre-gl/dist/maplibre-gl.css';
import * as turf from '@turf/turf';

interface DistrictDrilldownMapProps {
  districtId: string;
  districtName: string;
  bounds: LngLatBoundsLike;
  userLocation?: { lat: number; lng: number };
  onClose?: () => void;
  className?: string;
}

type Pollutant = 'NO2' | 'PM25' | 'SO2' | 'CO' | 'O3';

const POLLUTANT_LAYERS: Record<Pollutant, { label: string; layer: string }> = {
  NO2: { label: 'Nitrogen Dioxide', layer: 'no2_corrected' },
  PM25: { label: 'PM2.5', layer: 'pm25_corrected' },
  SO2: { label: 'Sulfur Dioxide', layer: 'so2_corrected' },
  CO: { label: 'Carbon Monoxide', layer: 'co_corrected' },
  O3: { label: 'Ozone', layer: 'o3_corrected' },
};

export function DrilldownMap({
  districtId,
  districtName,
  bounds,
  userLocation,
  onClose,
  className = '',
}: DistrictDrilldownMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [activePollutant, setActivePollutant] = useState<Pollutant>('NO2');
  const [showRadius, setShowRadius] = useState(false);
  const [currentDate] = useState<string>(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    if (!mapContainer.current) return;

    // Initialize map focused on district
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'osm-tiles': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap contributors',
          },
        },
        layers: [
          {
            id: 'osm-layer',
            type: 'raster',
            source: 'osm-tiles',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      bounds: bounds,
      fitBoundsOptions: { padding: 50 },
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.current.on('load', () => {
      if (!map.current) return;

      // Add pollutant layer
      updatePollutantLayer(activePollutant);

      // Add user location marker if provided
      if (userLocation) {
        new maplibregl.Marker({ color: '#E74C3C' })
          .setLngLat([userLocation.lng, userLocation.lat])
          .setPopup(
            new maplibregl.Popup().setHTML(
              '<div class="p-2 text-sm font-semibold">Your Location</div>'
            )
          )
          .addTo(map.current);
      }
    });

    return () => {
      map.current?.remove();
    };
  }, [bounds, userLocation, districtId]);

  // Update pollutant layer when selection changes
  useEffect(() => {
    if (!map.current?.isStyleLoaded()) return;
    updatePollutantLayer(activePollutant);
  }, [activePollutant, currentDate]);

  // Toggle 5km radius circle
  useEffect(() => {
    if (!map.current?.isStyleLoaded() || !userLocation) return;

    if (showRadius) {
      // Create 5km radius circle using Turf.js
      const center = turf.point([userLocation.lng, userLocation.lat]);
      const radius = 5; // kilometers
      const options = { steps: 64, units: 'kilometers' as const };
      const circle = turf.circle(center, radius, options);

      if (map.current.getSource('radius-circle')) {
        (map.current.getSource('radius-circle') as maplibregl.GeoJSONSource).setData(circle);
      } else {
        map.current.addSource('radius-circle', {
          type: 'geojson',
          data: circle,
        });

        map.current.addLayer({
          id: 'radius-fill',
          type: 'fill',
          source: 'radius-circle',
          paint: {
            'fill-color': '#0066CC',
            'fill-opacity': 0.1,
          },
        });

        map.current.addLayer({
          id: 'radius-outline',
          type: 'line',
          source: 'radius-circle',
          paint: {
            'line-color': '#0066CC',
            'line-width': 2,
            'line-dasharray': [2, 2],
          },
        });
      }
    } else {
      if (map.current.getLayer('radius-fill')) {
        map.current.removeLayer('radius-fill');
      }
      if (map.current.getLayer('radius-outline')) {
        map.current.removeLayer('radius-outline');
      }
      if (map.current.getSource('radius-circle')) {
        map.current.removeSource('radius-circle');
      }
    }
  }, [showRadius, userLocation]);

  function updatePollutantLayer(pollutant: Pollutant) {
    if (!map.current) return;

    const layerConfig = POLLUTANT_LAYERS[pollutant];

    // Remove existing pollutant layer
    if (map.current.getLayer('pollutant-layer')) {
      map.current.removeLayer('pollutant-layer');
    }
    if (map.current.getSource('pollutant-wms')) {
      map.current.removeSource('pollutant-wms');
    }

    // Add new pollutant layer
    map.current.addSource('pollutant-wms', {
      type: 'raster',
      tiles: [
        `http://localhost:8080/geoserver/air_risk/wms?service=WMS&version=1.1.1&request=GetMap&layers=air_risk:${layerConfig.layer}&bbox={bbox-epsg-3857}&width=256&height=256&srs=EPSG:3857&format=image/png&time=${currentDate}&transparent=true`,
      ],
      tileSize: 256,
    });

    map.current.addLayer({
      id: 'pollutant-layer',
      type: 'raster',
      source: 'pollutant-wms',
      paint: {
        'raster-opacity': 0.7,
      },
    });
  }

  return (
    <div className={cn('relative w-full h-full', className)}>
      {/* Map Container */}
      <div ref={mapContainer} className="map-container" />

      {/* Header */}
      <div className="absolute top-4 left-4 bg-white rounded-lg shadow-elevation-2 p-4 max-w-sm">
        <h3 className="font-semibold text-lg">{districtName}</h3>
        <p className="text-sm text-muted-foreground">District View - Premium</p>
      </div>

      {/* Pollutant Layer Switcher */}
      <div className="absolute top-4 right-4 bg-white rounded-lg shadow-elevation-2 p-3">
        <div className="flex items-center gap-2 mb-2">
          <Layers className="h-4 w-4" />
          <span className="font-semibold text-sm">Pollutant Layer</span>
        </div>
        <div className="flex flex-col gap-1">
          {(Object.keys(POLLUTANT_LAYERS) as Pollutant[]).map((pollutant) => (
            <button
              key={pollutant}
              onClick={() => setActivePollutant(pollutant)}
              className={cn(
                'px-3 py-2 text-sm rounded transition-colors text-left',
                activePollutant === pollutant
                  ? 'bg-brand-primary text-white'
                  : 'bg-gray-100 hover:bg-gray-200'
              )}
            >
              {POLLUTANT_LAYERS[pollutant].label}
            </button>
          ))}
        </div>
      </div>

      {/* 5km Radius Toggle (if user location available) */}
      {userLocation && (
        <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-elevation-2 p-3">
          <button
            onClick={() => setShowRadius(!showRadius)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded transition-colors',
              showRadius
                ? 'bg-brand-primary text-white'
                : 'bg-gray-100 hover:bg-gray-200'
            )}
          >
            <MapPin className="h-4 w-4" />
            <span className="text-sm font-medium">5km Analysis Radius</span>
          </button>
        </div>
      )}

      {/* Close Button */}
      {onClose && (
        <button
          onClick={onClose}
          className="absolute top-4 right-20 bg-white rounded-full p-2 shadow-elevation-2 hover:bg-gray-100 transition-colors"
          aria-label="Close district view"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
