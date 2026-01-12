/**
 * SatelliteLayer Component
 * 
 * Displays Sentinel-5P satellite imagery via Google Earth Engine tiles.
 * Supports multiple pollutants (NO2, SO2, CO, O3, etc.) with date selection.
 * 
 * @module components/layers/SatelliteLayer
 */

import { useEffect, useMemo, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import { useMap } from '@/contexts/MapContext';
import { useGEETiles, useGEEDates, type GEEPollutant } from '@/hooks/queries';

// =============================================================================
// Types
// =============================================================================

export interface SatelliteLayerProps {
  /** Pollutant to display */
  pollutant: GEEPollutant;
  /** Date for the imagery (YYYY-MM-DD), defaults to latest */
  date?: string;
  /** Whether the layer is visible */
  visible?: boolean;
  /** Layer opacity (0-1) */
  opacity?: number;
  /** Callback when tile data is loaded */
  onTileLoad?: (tileData: any, date: string) => void;
  /** Callback when loading state changes */
  onLoadingChange?: (isLoading: boolean) => void;
}

// =============================================================================
// Constants
// =============================================================================

const SOURCE_ID = 'sentinel5p-source';
const LAYER_ID = 'sentinel5p-layer';

// =============================================================================
// Component
// =============================================================================

export function SatelliteLayer({
  pollutant,
  date,
  visible = true,
  opacity = 0.7,
  onTileLoad,
  onLoadingChange,
}: SatelliteLayerProps) {
  const { map, isLoaded } = useMap();
  
  // Get available dates if no date specified
  const { data: datesData } = useGEEDates(pollutant, {
    enabled: !date, // Only fetch if no date provided
  });
  
  // Use provided date or latest available
  const targetDate = useMemo(() => {
    if (date) return date;
    return datesData?.latest_date ?? null;
  }, [date, datesData]);

  // Fetch tile URL
  const { 
    data: tileData, 
    isLoading,
    isError,
    error,
  } = useGEETiles(pollutant, targetDate ?? '', {
    enabled: !!targetDate && !!pollutant,
  });
  
  // Debug logging
  useEffect(() => {
    console.log('[SatelliteLayer] State:', {
      pollutant,
      targetDate,
      isLoading,
      isError,
      hasTileUrl: !!tileData?.tiles?.url_template,
      tileUrl: tileData?.tiles?.url_template,
      imageCount: tileData?.image_count,
      visualization: tileData?.visualization,
      error: error?.message,
    });
  }, [pollutant, targetDate, isLoading, isError, tileData, error]);

  // Notify loading state
  useEffect(() => {
    onLoadingChange?.(isLoading);
  }, [isLoading, onLoadingChange]);

  // Notify when tile loaded
  useEffect(() => {
    if (tileData?.tiles?.url_template && targetDate) {
      onTileLoad?.(tileData.tiles.url_template, targetDate);
    }
  }, [tileData, targetDate, onTileLoad]);

  // Add/update source and layer (only when tile URL changes)
  useEffect(() => {
    if (!map || !isLoaded || !tileData?.tiles?.url_template) return;
    
    // Check if we have valid imagery
    if (tileData.image_count === 0) {
      console.warn(`[SatelliteLayer] No imagery available for ${pollutant} on ${targetDate}`);
      return;
    }
    
    // Transform tile URL to ensure proper placeholder format
    let tileUrl = tileData.tiles.url_template;
    
    // Replace various placeholder formats with standard {x}/{y}/{z}
    tileUrl = tileUrl
      .replace(/\{zoom\}/g, '{z}')
      .replace(/\{ZOOM\}/g, '{z}')
      .replace(/\$\{z\}/g, '{z}')
      .replace(/\$\{x\}/g, '{x}')
      .replace(/\$\{y\}/g, '{y}');
    
    console.log('[SatelliteLayer] Adding new tile source:', tileUrl);

    // Remove existing layer/source
    if (map.getLayer(LAYER_ID)) {
      map.removeLayer(LAYER_ID);
    }
    if (map.getSource(SOURCE_ID)) {
      map.removeSource(SOURCE_ID);
    }

    // Add raster tile source
    map.addSource(SOURCE_ID, {
      type: 'raster',
      tiles: [tileUrl],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 10,  // Sentinel-5P is low resolution (~7km), limit max zoom
      attribution: tileData.tiles.attribution || '© Google Earth Engine / Copernicus Sentinel-5P',
    });

    // Add raster layer at the TOP of the layer stack
    map.addLayer({
      id: LAYER_ID,
      type: 'raster',
      source: SOURCE_ID,
      paint: {
        'raster-opacity': opacity,
      },
    });
    
    console.log('[SatelliteLayer] Layer added with initial opacity:', opacity);

    return () => {
      if (!map) return;
      try {
        if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
        if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      } catch (e) {
        // Map might be destroyed
      }
    };
  }, [map, isLoaded, tileData?.tiles?.url_template, tileData?.image_count]);

  // Update opacity separately (without recreating layer)
  useEffect(() => {
    if (!map || !isLoaded || !map.getLayer(LAYER_ID)) return;
    
    map.setPaintProperty(LAYER_ID, 'raster-opacity', opacity);
  }, [map, isLoaded, opacity]);

  // Update visibility separately
  useEffect(() => {
    if (!map || !isLoaded || !map.getLayer(LAYER_ID)) return;
    
    map.setLayoutProperty(LAYER_ID, 'visibility', visible ? 'visible' : 'none');
  }, [map, isLoaded, visible]);

  // Handle errors
  if (isError) {
    console.error(`[SatelliteLayer] Failed to load ${pollutant} tiles for ${targetDate}`, error);
  }

  // Tooltip popup for sampling values
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const sampleTimerRef = useRef<number | null>(null);
  const mountedRef = useRef(true);

  // Click sampling for raster layer (better performance than hover)
  useEffect(() => {
    if (!map || !isLoaded || !visible || !tileData?.tiles?.url_template || !targetDate) return;

    mountedRef.current = true;
    const popup = new maplibregl.Popup({ closeOnClick: true, closeButton: true });
    popupRef.current = popup;

    const handleClick = async (e: maplibregl.MapMouseEvent) => {
      const lon = e.lngLat.lng;
      const lat = e.lngLat.lat;
      
      // Show loading state
      popup.setLngLat(e.lngLat).setHTML(`<div style="padding: 4px; text-align: center;"><b>${pollutant}</b><br/>Loading...</div>`).addTo(map);
      
      try {
        const params = new URLSearchParams({
          pollutant,
          date: targetDate,
          lon: lon.toString(),
          lat: lat.toString(),
          composite: (tileData?.composite_days ?? 7).toString(),
        });
        const res = await fetch(`/api/v1/air-quality/gee/value/?${params.toString()}`);
        const json = await res.json();
        if (mountedRef.current && json?.status === 'success') {
          const value = json.data?.value;
          const unit = json.data?.unit;
          const formattedValue = typeof value === 'number' ? value.toFixed(4) : 'n/a';
          popup.setHTML(`
            <div style="padding: 8px; min-width: 120px;">
              <div style="font-weight: 600; margin-bottom: 4px; color: #8b5cf6;">${pollutant}</div>
              <div style="font-size: 18px; font-weight: 700; color: #1f2937;">${formattedValue}</div>
              <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">${unit ?? ''}</div>
              <div style="font-size: 10px; color: #9ca3af; margin-top: 4px; border-top: 1px solid #e5e7eb; padding-top: 4px;">Click elsewhere to close</div>
            </div>
          `);
        } else if (mountedRef.current) {
          popup.setHTML(`<div style="padding: 8px; color: #ef4444;">No data available</div>`);
        }
      } catch (err) {
        if (mountedRef.current) {
          popup.setHTML(`<div style="padding: 8px; color: #ef4444;">Error fetching data</div>`);
        }
      }
    };

    map.on('click', handleClick);

    return () => {
      mountedRef.current = false;
      try {
        map.off('click', handleClick);
      } catch (e) {
        // ignore
      }
      if (popupRef.current) popupRef.current.remove();
      if (sampleTimerRef.current) window.clearTimeout(sampleTimerRef.current);
    };
  }, [map, isLoaded, visible, pollutant, targetDate, tileData?.tiles?.url_template]);

  return null;
}

export default SatelliteLayer;

// =============================================================================
// Pollutant Info Helper
// =============================================================================

export const POLLUTANT_INFO: Record<GEEPollutant, { name: string; unit: string; description: string }> = {
  NO2: {
    name: 'Nitrogen Dioxide',
    unit: 'mol/m²',
    description: 'Tropospheric NO2 from vehicles and industry',
  },
  SO2: {
    name: 'Sulfur Dioxide',
    unit: 'mol/m²',
    description: 'SO2 from power plants and volcanic activity',
  },
  CO: {
    name: 'Carbon Monoxide',
    unit: 'mol/m²',
    description: 'CO from incomplete combustion',
  },
  O3: {
    name: 'Ozone',
    unit: 'mol/m²',
    description: 'Ground-level ozone, a key component of smog',
  },
  HCHO: {
    name: 'Formaldehyde',
    unit: 'mol/m²',
    description: 'HCHO from biomass burning and oxidation',
  },
  CH4: {
    name: 'Methane',
    unit: 'ppb',
    description: 'CH4 from agriculture and fossil fuels',
  },
  AER_AI: {
    name: 'Aerosol Index',
    unit: 'index',
    description: 'Absorbing aerosol index indicating dust/smoke',
  },
};
