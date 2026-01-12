/**
 * UnifiedMap Component
 * 
 * Comprehensive map displaying all spatial data layers:
 * - District choropleth (PM2.5/AQI exposure data)
 * - Province boundaries
 * - Ground monitoring stations (~370+)
 * - Sentinel-5P satellite imagery (GEE tiles)
 * 
 * @module features/map/components/UnifiedMap
 */

import { useCallback, useMemo, useState } from 'react';
import { MapBase, MAP_STYLES } from '@/components/map';
import {
  DistrictsLayer,
  ProvincesLayer,
  StationsLayer,
  SatelliteLayer,
  RadiusCircleLayer,
  type DistrictExposureProperties,
} from '@/components/layers';
import { GEEExposureLayer } from '@/components/layers/GEEExposureLayer';
import { LayerControls, UnifiedLegend, DistrictDetailPanel } from '@/components/ui';
import { StationDetailPanel } from '@/components/ui/StationDetailPanel';
import { useGEEDates, useStations, useSatelliteExposure } from '@/hooks/queries';
import type { StationProperties } from '@/types/models';
import type { Map as MapLibreMap } from 'maplibre-gl';
import { useMapStore } from '@/store'; // ✅ FIXED: Use Zustand instead of local state
import type { GEEExposureResult } from '@/api/geeExposure';
import { calculateDistrictCenter, LEGEND_ITEMS, PM25_LEGEND_ITEMS } from '@/constants/map';

// =============================================================================
// Types
// =============================================================================

export interface UnifiedMapProps {
  /** Initial date for exposure data (YYYY-MM-DD) */
  date?: string;
  /** Optional CSS class name */
  className?: string;
  /** Callback when map loads */
  onMapLoad?: (map: MapLibreMap) => void;
  /** Callback when district is selected */
  onDistrictSelect?: (district: DistrictExposureProperties) => void;
  /** Callback when station is selected */
  onStationSelect?: (station: StationProperties) => void;
  /** Enable premium features (GEE exposure) */
  enablePremiumFeatures?: boolean;
}

// =============================================================================
// Component
// =============================================================================

export function UnifiedMap({
  date,
  onMapLoad,
  onDistrictSelect,
  onStationSelect,
  enablePremiumFeatures = false,
}: UnifiedMapProps) {
  // ✅ FIXED: Replace 8 local useState with Zustand store
  const layers = useMapStore((state) => state.layers);
  const setLayers = useMapStore((state) => state.setLayers);
  const viewMode = useMapStore((state) => state.viewMode);
  const selectedProvince = useMapStore((state) => state.selectedProvince);
  const pollutant = useMapStore((state) => state.pollutant);
  const setPollutant = useMapStore((state) => state.setPollutant);
  const satelliteDate = useMapStore((state) => state.satelliteDate);
  const setSatelliteDate = useMapStore((state) => state.setSatelliteDate);
  const satelliteOpacity = useMapStore((state) => state.satelliteOpacity);
  const setSatelliteOpacity = useMapStore((state) => state.setSatelliteOpacity);
  const satelliteLoading = useMapStore((state) => state.satelliteLoading);
  const setSatelliteLoading = useMapStore((state) => state.setSatelliteLoading);
  const selectedStation = useMapStore((state) => state.selectedStation);
  const setSelectedStation = useMapStore((state) => state.setSelectedStation);
  const selectedDistrict = useMapStore((state) => state.selectedDistrict);
  const setSelectedDistrict = useMapStore((state) => state.setSelectedDistrict);
  const backToProvinces = useMapStore((state) => state.backToProvinces);

  // Fetch available dates for selected pollutant
  const { data: datesData } = useGEEDates(pollutant, {
    enabled: layers.satellite,
  });

  // Calculate district center point from selected district geometry
  const districtCenter = useMemo(() => {
    if (!selectedDistrict?.geometry) return null;
    return calculateDistrictCenter(selectedDistrict.geometry);
  }, [selectedDistrict?.geometry]);

  // Fetch satellite exposure for selected district location
  // TODO: This uses old calculation method - needs to be updated with new exposure data
  const { data: satelliteExposure, isLoading: exposureLoading } = useSatelliteExposure(
    districtCenter ? { lat: districtCenter[1], lon: districtCenter[0], daysBack: 7 } : {},
    { enabled: false } // Disabled: old exposure calculation method
  );


  // Get station count for display
  const { data: stations } = useStations();
  const stationCount = stations?.length ?? 0;

  // GEE Exposure state (Premium feature)
  const [geeExposureResult, setGeeExposureResult] = useState<GEEExposureResult | null>(null);
  const [geeDisplayMode, setGeeDisplayMode] = useState<'exposure' | 'aqi'>('exposure');
  const [geeVisible, setGeeVisible] = useState(true);
  const [geeOpacity, setGeeOpacity] = useState(0.7);

  // Districts API removed - now on dedicated /exposure page

  // Available dates for date picker
  const availableDates = useMemo(() => {
    return datesData?.available_dates ?? [];
  }, [datesData]);

  // Handle district click - show detail panel
  const handleDistrictClick = useCallback(
    (district: DistrictExposureProperties) => {
      console.log('[UnifiedMap] District clicked:', district.district_name);
      setSelectedDistrict(district);
      onDistrictSelect?.(district);
    },
    [onDistrictSelect, setSelectedDistrict]
  );

  // Close district detail panel
  const handleCloseDistrictDetail = useCallback(() => {
    setSelectedDistrict(null);
  }, [setSelectedDistrict]);

  // Handle station click
  const handleStationClick = useCallback(
    (station: StationProperties) => {
      console.log('[UnifiedMap] Station clicked:', station.name);
      setSelectedStation(station);
      onStationSelect?.(station);
    },
    [onStationSelect]
  );

  const handleCloseStationDetail = useCallback(() => {
    setSelectedStation(null);
  }, [setSelectedStation]);

  // Back to provinces view - use Zustand action
  const handleBackToProvinces = useCallback(() => {
    backToProvinces();
  }, [backToProvinces]);

  // Handle province click - drill down to districts
  const handleProvinceClick = useCallback(
    (province: any) => {
      console.log('[UnifiedMap] Province clicked:', province.name);
      useMapStore.setState({
        selectedProvince: province.name,
        viewMode: 'districts',
      });
    },
    []
  );

  // Handle satellite tile loaded
  const handleSatelliteTileLoad = useCallback((loadedDate: string) => {
    console.log(`[UnifiedMap] Satellite tiles loaded: ${pollutant} for ${loadedDate}`);
  }, [pollutant]);

  return (
    <div className="unified-map relative w-full h-full">
      {/* Map with all layers */}
      <MapBase
        style={MAP_STYLES.CARTO_LIGHT}
        center={[69.3451, 30.3753]}
        zoom={5}
        onLoad={onMapLoad}
        containerStyle={{ width: '100%', height: '100%' }}
      >
        {/* Provinces layer - visible in province view */}
        {viewMode === 'provinces' && (
          <ProvincesLayer onProvinceClick={handleProvinceClick} />
        )}

        {/* Districts layer - visible when drilling down */}
        {/* NOTE: This shows OLD precalculated exposure from database. */}
        {/* For premium users, GEE exposure (below) should be used instead. */}
        {/* Hidden when GEE exposure result is active for premium users */}
        {viewMode === 'districts' && !(enablePremiumFeatures && geeExposureResult) && (
          <DistrictsLayer
            province={selectedProvince ?? undefined}
            date={date}
            colorMode="pm25"
            selectedDistrictId={selectedDistrict?.district_id}
            onDistrictClick={handleDistrictClick}
          />
        )}

        {/* 5km radius circle around selected district */}
        {viewMode === 'districts' && selectedDistrict && (
          <RadiusCircleLayer
            center={[selectedDistrict.geometry?.coordinates?.[0], selectedDistrict.geometry?.coordinates?.[1]] as [number, number] | null}
            radiusKm={5}
            color="#0EA5E9"
            opacity={0.15}
            visible={true}
          />
        )}

        {/* Satellite imagery - render AFTER districts so it appears on top */}
        {layers.satellite && (
          <SatelliteLayer
            pollutant={pollutant}
            date={satelliteDate}
            visible={layers.satellite}
            opacity={satelliteOpacity}
            onTileLoad={handleSatelliteTileLoad}
            onLoadingChange={setSatelliteLoading}
          />
        )}

        {/* Stations layer - always on top */}
        <StationsLayer
          visible={layers.stations}
          clustered={true}
          onStationClick={handleStationClick}
        />

        {/* GEE Exposure Layer - Premium only */}
        {enablePremiumFeatures && geeExposureResult && (
          <GEEExposureLayer
            exposureResult={geeExposureResult}
            mode={geeDisplayMode}
            visible={geeVisible}
            opacity={geeOpacity}
          />
        )}
      </MapBase>

      {/* Premium Exposure Control moved to dedicated /exposure page */}

      {/* Layer Controls - adjusted z-index */}
      <LayerControls
        layers={layers}
        onLayerChange={setLayers}
        pollutant={pollutant}
        onPollutantChange={setPollutant}
        date={satelliteDate}
        availableDates={availableDates}
        onDateChange={setSatelliteDate}
        satelliteOpacity={satelliteOpacity}
        onOpacityChange={setSatelliteOpacity}
        satelliteLoading={satelliteLoading}
        stationCount={stationCount}
        viewMode={viewMode}
        selectedProvince={selectedProvince ?? undefined}
        onBackToProvinces={handleBackToProvinces}
      />

      {/* PM2.5 Legend - Professional Gradient */}
      <div className="absolute bottom-6 right-6 bg-white/95 backdrop-blur-xl p-4 rounded-xl shadow-2xl border border-gray-200 z-1000 min-w-[280px]">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-bold text-gray-800 m-0">Air Quality Index</h4>
          <span className="text-xs text-gray-500">PM2.5</span>
        </div>

        {/* Gradient Bar */}
        <div className="relative h-6 rounded-lg overflow-hidden mb-2" style={{
          background: 'linear-gradient(to right, #00e400 0%, #ffff00 20%, #ff7e00 40%, #ff0000 60%, #8f3f97 80%, #7e0023 100%)'
        }}>
          <div className="absolute inset-0 border-2 border-white/30 rounded-lg pointer-events-none" />
        </div>

        {/* Value Labels */}
        <div className="flex justify-between text-[10px] font-medium text-gray-600 mb-3">
          <span>0</span>
          <span>50</span>
          <span>100</span>
          <span>150</span>
          <span>200</span>
          <span>300+</span>
        </div>

        {/* Category Labels */}
        <div className="space-y-1">
          {PM25_LEGEND_ITEMS.map((item) => (
            <div key={item.label} className="flex items-center gap-1.5 group">
              <div
                className="w-2.5 h-2.5 rounded-sm shadow-sm border border-white/50"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-[10px] text-gray-700 group-hover:text-gray-900 transition-colors">
                {item.min}-{item.max} {item.label}
              </span>
            </div>
          ))}
        </div>

        <div className="mt-2 pt-2 border-t border-gray-200 text-[9px] text-gray-500 text-right">
          WHO Guidelines
        </div>
      </div>

      {/* Unified Legend - Compact horizontal at bottom center */}
      <UnifiedLegend
        satellite={layers.satellite ? { pollutant, visible: layers.satellite } : undefined}
        geeExposure={geeExposureResult ? { mode: geeDisplayMode, visible: geeVisible } : undefined}
        groundStations={layers.stations}
      />

      {/* Station Count Badge */}
      {layers.stations && (
        <div className="absolute top-24 left-6 bg-white/95 backdrop-blur-xl px-4 py-2 rounded-xl shadow-lg border border-gray-200 z-1000 text-sm font-semibold text-gray-700">
          <span className="text-green-600">●</span> {stationCount} Active Stations
        </div>
      )}

      {/* Station Detail Panel */}
      {selectedStation && (
        <StationDetailPanel
          station={selectedStation}
          onClose={handleCloseStationDetail}
        />
      )}

      {/* District Detail Panel */}
      <DistrictDetailPanel
        district={selectedDistrict}
        isOpen={!!selectedDistrict}
        onClose={handleCloseDistrictDetail}
        satelliteExposure={satelliteExposure}
        exposureLoading={exposureLoading}
      />
    </div>
  );
}

export default UnifiedMap;
