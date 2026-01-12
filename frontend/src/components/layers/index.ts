/**
 * Layer Components
 * 
 * GeoJSON-based map layers using TanStack Query
 */

export { DistrictsLayer } from './DistrictsLayer';
export type { 
  DistrictsLayerProps, 
  DistrictExposureProperties,
  DistrictProperties,  // Legacy type for backwards compatibility
} from './DistrictsLayer';

export { ProvincesLayer } from './ProvincesLayer';
export type { ProvincesLayerProps, ProvinceProperties } from './ProvincesLayer';

export { StationsLayer } from './StationsLayer';
export type { StationsLayerProps } from './StationsLayer';

export { SatelliteLayer, POLLUTANT_INFO } from './SatelliteLayer';

export { RadiusCircleLayer } from './RadiusCircleLayer';
export type { RadiusCircleLayerProps } from './RadiusCircleLayer';
export type { SatelliteLayerProps } from './SatelliteLayer';

export { GEEExposureLayer } from './GEEExposureLayer';
export type { GEEExposureLayerProps } from './GEEExposureLayer';
