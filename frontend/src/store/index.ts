/**
 * Store Barrel Export
 * 
 * Centralized exports for all Zustand stores.
 * 
 * @module store
 */

// Map Store
export {
  useMapStore,
  useLayerVisibility,
  useViewMode,
  useSelectedProvince,
  useSatelliteControls,
  useSelectedStation,
} from './mapStore';

export type { MapStore, LayerState } from './mapStore';

// Auth Store
export {
  useAuthStore,
  useUser,
  useIsAuthenticated,
  useIsPremium,
  useTier,
  useAuthError,
} from './authStore';

export type { AuthStore } from './authStore';

// Report Store
export {
  useReportStore,
  useReports,
  useGenerationState,
  useIsGenerating,
} from './reportStore';

export type { ReportStore, ReportGenerationState } from './reportStore';

