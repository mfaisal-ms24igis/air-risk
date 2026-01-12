import { useEffect, useRef, useState } from 'react';
import maplibregl, { Map as MapLibreMap, LngLatBoundsLike } from 'maplibre-gl';
import { useUserTier } from '@/hooks/useUserTier';
import 'maplibre-gl/dist/maplibre-gl.css';

const PAKISTAN_BOUNDS: LngLatBoundsLike = [
  [60.87, 23.63], // Southwest coordinates
  [77.84, 37.09], // Northeast coordinates
];

const PAKISTAN_CENTER: [number, number] = [69.35, 30.38];

interface WMSLayerConfig {
  layerName: string;
  pollutant: string;
  visible: boolean;
}

interface PakistanBaseMapProps {
  onDistrictClick?: (districtId: string, districtName: string, bounds: LngLatBoundsLike) => void;
  className?: string;
  enableInteraction?: boolean;
}

export function PakistanBaseMap({
  onDistrictClick,
  className = '',
  enableInteraction = true,
}: PakistanBaseMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [currentDate, setCurrentDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const { isPremium } = useUserTier();

  useEffect(() => {
    if (!mapContainer.current) return;

    // Initialize map
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
      center: PAKISTAN_CENTER,
      zoom: 5,
      maxBounds: PAKISTAN_BOUNDS,
    });

    // Add navigation controls
    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.current.addControl(new maplibregl.ScaleControl(), 'bottom-left');

    // Add WMS risk zone layer from GeoServer
    map.current.on('load', () => {
      if (!map.current) return;

      // Add WMS source for corrected NO2 data
      map.current.addSource('geoserver-wms', {
        type: 'raster',
        tiles: [
          `http://localhost:8080/geoserver/air_risk/wms?service=WMS&version=1.1.1&request=GetMap&layers=air_risk:no2_corrected&bbox={bbox-epsg-3857}&width=256&height=256&srs=EPSG:3857&format=image/png&time=${currentDate}&transparent=true`,
        ],
        tileSize: 256,
      });

      map.current.addLayer({
        id: 'risk-zones',
        type: 'raster',
        source: 'geoserver-wms',
        paint: {
          'raster-opacity': 0.7,
        },
      });

      // Add district boundaries from API
      fetch('http://127.0.0.1:8000/api/v1/air-quality/districts/')
        .then((res) => res.json())
        .then((data) => {
          if (!map.current) return;

          const features = data.results.map((district: any) => ({
            type: 'Feature',
            properties: {
              id: district.id,
              name: district.name,
              aqi: district.latest_aqi,
            },
            geometry: district.geometry,
          }));

          map.current.addSource('districts', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features,
            },
          });

          // District fill layer
          map.current.addLayer({
            id: 'districts-fill',
            type: 'fill',
            source: 'districts',
            paint: {
              'fill-color': 'transparent',
              'fill-opacity': 0.1,
            },
          });

          // District outline layer
          map.current.addLayer({
            id: 'districts-outline',
            type: 'line',
            source: 'districts',
            paint: {
              'line-color': '#0066CC',
              'line-width': 2,
              'line-opacity': 0.6,
            },
          });

          // Add hover effect
          map.current.on('mouseenter', 'districts-fill', () => {
            if (map.current) {
              map.current.getCanvas().style.cursor = 'pointer';
            }
          });

          map.current.on('mouseleave', 'districts-fill', () => {
            if (map.current) {
              map.current.getCanvas().style.cursor = '';
            }
          });

          // Add click handler for PREMIUM users
          if (isPremium && enableInteraction && onDistrictClick) {
            map.current.on('click', 'districts-fill', (e) => {
              if (!e.features || e.features.length === 0) return;

              const feature = e.features[0];
              const districtId = feature.properties?.id;
              const districtName = feature.properties?.name;

              if (districtId && districtName && feature.geometry.type === 'Polygon') {
                // Calculate bounds from geometry
                const coordinates = feature.geometry.coordinates[0];
                const bounds = coordinates.reduce(
                  (bounds: any, coord: any) => {
                    return bounds.extend(coord);
                  },
                  new maplibregl.LngLatBounds(coordinates[0], coordinates[0])
                );

                onDistrictClick(districtId, districtName, [
                  [bounds.getWest(), bounds.getSouth()],
                  [bounds.getEast(), bounds.getNorth()],
                ]);
              }
            });
          }

          // Add popup on hover showing AQI
          const popup = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false,
          });

          map.current.on('mousemove', 'districts-fill', (e) => {
            if (!e.features || e.features.length === 0) return;

            const feature = e.features[0];
            const name = feature.properties?.name;
            const aqi = feature.properties?.aqi;

            if (name && aqi !== undefined) {
              popup
                .setLngLat(e.lngLat)
                .setHTML(
                  `<div class="p-2">
                    <div class="font-semibold">${name}</div>
                    <div class="text-sm">AQI: ${Math.round(aqi)}</div>
                  </div>`
                )
                .addTo(map.current!);
            }
          });

          map.current.on('mouseleave', 'districts-fill', () => {
            popup.remove();
          });
        })
        .catch((error) => {
          console.error('Failed to load districts:', error);
        });

      // Add station markers
      fetch('http://127.0.0.1:8000/api/v1/air-quality/stations/')
        .then((res) => res.json())
        .then((data) => {
          if (!map.current) return;

          const features = data.results.map((station: any) => ({
            type: 'Feature',
            properties: {
              id: station.id,
              name: station.name,
              provider: station.provider,
            },
            geometry: {
              type: 'Point',
              coordinates: station.location.coordinates,
            },
          }));

          map.current.addSource('stations', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features,
            },
            cluster: true,
            clusterMaxZoom: 10,
            clusterRadius: 50,
          });

          // Clustered points
          map.current.addLayer({
            id: 'clusters',
            type: 'circle',
            source: 'stations',
            filter: ['has', 'point_count'],
            paint: {
              'circle-color': [
                'step',
                ['get', 'point_count'],
                '#00A651',
                10,
                '#F39C12',
                30,
                '#E74C3C',
              ],
              'circle-radius': ['step', ['get', 'point_count'], 15, 10, 20, 30, 25],
              'circle-stroke-width': 2,
              'circle-stroke-color': '#fff',
            },
          });

          // Cluster count
          map.current.addLayer({
            id: 'cluster-count',
            type: 'symbol',
            source: 'stations',
            filter: ['has', 'point_count'],
            layout: {
              'text-field': '{point_count_abbreviated}',
              'text-font': ['Open Sans Semibold'],
              'text-size': 12,
            },
            paint: {
              'text-color': '#ffffff',
            },
          });

          // Unclustered points
          map.current.addLayer({
            id: 'unclustered-point',
            type: 'circle',
            source: 'stations',
            filter: ['!', ['has', 'point_count']],
            paint: {
              'circle-color': '#0066CC',
              'circle-radius': 8,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#fff',
            },
          });

          // Station popup
          map.current.on('click', 'unclustered-point', (e) => {
            if (!e.features || e.features.length === 0) return;

            const coordinates = (e.features[0].geometry as any).coordinates.slice();
            const name = e.features[0].properties?.name;
            const provider = e.features[0].properties?.provider;

            new maplibregl.Popup()
              .setLngLat(coordinates)
              .setHTML(
                `<div class="p-3">
                  <div class="font-semibold text-sm">${name}</div>
                  <div class="text-xs text-gray-600 mt-1">Provider: ${provider}</div>
                </div>`
              )
              .addTo(map.current!);
          });
        })
        .catch((error) => {
          console.error('Failed to load stations:', error);
        });
    });

    // Cleanup
    return () => {
      map.current?.remove();
    };
  }, [currentDate, isPremium, enableInteraction, onDistrictClick]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className={`map-container ${className}`} />
    </div>
  );
}
