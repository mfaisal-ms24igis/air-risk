/**
 * Hooks Module
 * 
 * TanStack Query-based hooks for data fetching
 */

// =============================================================================
// NEW: Typed Query Hooks (Recommended)
// =============================================================================

export * from './queries';

// =============================================================================
// Legacy: GeoJSON hooks (maintained for compatibility)
// =============================================================================

// Primary GeoJSON hook (TanStack Query)
export {
  useGeoJSON,
  useProvincesGeoJSON as useProvincesGeoJSONLegacy,
  useDistrictsGeoJSON as useDistrictsGeoJSONLegacy,
  useStationsGeoJSON as useStationsGeoJSONLegacy,
} from './useGeoJSON';
export type {
  UseGeoJSONOptions,
  UseGeoJSONResult,
  TypedFeatureCollection,
  TypedFeature,
} from './useGeoJSON';

// Legacy hooks (deprecated - use TanStack Query hooks instead)
/** @deprecated Use useGeoJSON from TanStack Query instead */
export { useFetchGeoJSON } from './useFetchGeoJSON';
export type { UseFetchGeoJSONOptions, UseFetchGeoJSONResult } from './useFetchGeoJSON';

/** @deprecated Use useQuery from TanStack Query instead */
export { useFetch } from './useFetch';
export type { UseFetchOptions, UseFetchResult } from './useFetch';

// =============================================================================
// UI Hooks
// =============================================================================

export { useModal } from './useModal';
export type { UseModalReturn } from './useModal';
