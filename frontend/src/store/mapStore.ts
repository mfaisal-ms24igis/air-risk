/**
 * Map Store - Zustand
 * 
 * Global state for map UI controls and selections.
 * Replaces scattered useState across UnifiedMap.
 * 
 * @module store/mapStore
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { StationProperties } from '@/types/models';
import type { GEEPollutant } from '@/hooks/queries';

// =============================================================================
// Types
// =============================================================================

export interface LayerState {
  districts: boolean;
  stations: boolean;
  satellite: boolean;
}

export interface MapStore {
  // Layer visibility
  layers: LayerState;
  setLayers: (layers: LayerState | ((prev: LayerState) => LayerState)) => void;
  toggleLayer: (layer: keyof LayerState) => void;

  // View mode & navigation
  viewMode: 'provinces' | 'districts';
  selectedProvince: string | null;
  setViewMode: (mode: 'provinces' | 'districts') => void;
  setSelectedProvince: (province: string | null) => void;
  backToProvinces: () => void;

  // Satellite controls
  pollutant: GEEPollutant;
  satelliteDate: string | undefined;
  satelliteOpacity: number;
  satelliteLoading: boolean;
  setPollutant: (pollutant: GEEPollutant) => void;
  setSatelliteDate: (date: string | undefined) => void;
  setSatelliteOpacity: (opacity: number) => void;
  setSatelliteLoading: (loading: boolean) => void;

  // Station selection
  selectedStation: StationProperties | null;
  setSelectedStation: (station: StationProperties | null) => void;

  // District selection (for detail panel)
  selectedDistrict: any | null;
  setSelectedDistrict: (district: any | null) => void;

  // Reset all state
  reset: () => void;
}

// =============================================================================
// Initial State
// =============================================================================

const initialState = {
  layers: {
    districts: true,
    stations: true,
    satellite: false, // Off by default (heavy)
  },
  viewMode: 'provinces' as const,
  selectedProvince: null,
  pollutant: 'NO2' as GEEPollutant,
  satelliteDate: undefined,
  satelliteOpacity: 0.7,
  satelliteLoading: false,
  selectedStation: null,
  selectedDistrict: null,
};

// =============================================================================
// Store
// =============================================================================

export const useMapStore = create<MapStore>()(
  devtools(
    persist(
      (set) => ({
        ...initialState,

        // Layer controls
        setLayers: (layers) =>
          set((state) => ({
            layers: typeof layers === 'function' ? layers(state.layers) : layers,
          })),

        toggleLayer: (layer) =>
          set((state) => ({
            layers: {
              ...state.layers,
              [layer]: !state.layers[layer],
            },
          })),

        // View mode
        setViewMode: (mode) => set({ viewMode: mode }),

        setSelectedProvince: (province) => set({ selectedProvince: province }),

        backToProvinces: () =>
          set({
            viewMode: 'provinces',
            selectedProvince: null,
          }),

        // Satellite
        setPollutant: (pollutant) => set({ pollutant }),
        setSatelliteDate: (date) => set({ satelliteDate: date }),
        setSatelliteOpacity: (opacity) => set({ satelliteOpacity: opacity }),
        setSatelliteLoading: (loading) => set({ satelliteLoading: loading }),

        // Station
        setSelectedStation: (station) => set({ selectedStation: station }),

        // District
        setSelectedDistrict: (district) => set({ selectedDistrict: district }),

        // Reset
        reset: () => set(initialState),
      }),
      {
        name: 'map-store',
        // Only persist layer visibility and view preferences
        partialize: (state) => ({
          layers: state.layers,
          satelliteOpacity: state.satelliteOpacity,
          pollutant: state.pollutant,
        }),
      }
    ),
    { name: 'MapStore' }
  )
);

// =============================================================================
// Selectors (for optimized re-renders)
// =============================================================================

export const useLayerVisibility = () => useMapStore((state) => state.layers);
export const useViewMode = () => useMapStore((state) => state.viewMode);
export const useSelectedProvince = () => useMapStore((state) => state.selectedProvince);
export const useSatelliteControls = () =>
  useMapStore((state) => ({
    pollutant: state.pollutant,
    date: state.satelliteDate,
    opacity: state.satelliteOpacity,
    loading: state.satelliteLoading,
  }));
export const useSelectedStation = () => useMapStore((state) => state.selectedStation);

