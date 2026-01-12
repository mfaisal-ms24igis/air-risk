/**
 * SatelliteLegend Component
 * 
 * Displays color scale legend for Sentinel-5P satellite data
 * with proper units and value ranges.
 */

import type { GEEPollutant } from '@/hooks/queries';

interface SatelliteLegendProps {
  pollutant: GEEPollutant;
  visible?: boolean;
}

// Legend configurations matching GEE visualization
const SATELLITE_LEGENDS: Record<GEEPollutant, {
  title: string;
  unit: string;
  min: number;
  max: number;
  colors: string[];
  labels: string[];
}> = {
  NO2: {
    title: 'Nitrogen Dioxide',
    unit: 'mol/m²',
    min: 0.0,
    max: 0.0002,
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000', '#800000'],
    labels: ['0', '0.000025', '0.00005', '0.000075', '0.0001', '0.00015', '0.0002'],
  },
  SO2: {
    title: 'Sulfur Dioxide',
    unit: 'mol/m²',
    min: 0.0,
    max: 0.0005,
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['0', '0.0001', '0.0002', '0.0003', '0.0004', '0.0005'],
  },
  CO: {
    title: 'Carbon Monoxide',
    unit: 'mol/m²',
    min: 0.0,
    max: 0.05,
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['0', '0.01', '0.02', '0.03', '0.04', '0.05'],
  },
  O3: {
    title: 'Ozone',
    unit: 'mol/m²',
    min: 0.1,
    max: 0.14,
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['0.10', '0.11', '0.12', '0.13', '0.14'],
  },
  HCHO: {
    title: 'Formaldehyde',
    unit: 'mol/m²',
    min: 0.0,
    max: 0.0003,
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['0', '0.00005', '0.0001', '0.00015', '0.0002', '0.00025', '0.0003'],
  },
  CH4: {
    title: 'Methane',
    unit: 'ppb',
    min: 1750,
    max: 1950,
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['1750', '1800', '1850', '1900', '1950'],
  },
  AER_AI: {
    title: 'Aerosol Index',
    unit: 'index',
    min: -1,
    max: 2.0,
    colors: ['#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000', '#800000'],
    labels: ['-1', '0', '0.5', '1', '1.5', '2'],
  },
};

export function SatelliteLegend({ pollutant, visible = true }: SatelliteLegendProps) {
  if (!visible) return null;

  const legend = SATELLITE_LEGENDS[pollutant];
  if (!legend) return null;

  return (
    <div className="bg-white/95 backdrop-blur-xl p-2.5 rounded-lg shadow-lg border border-gray-200 min-w-[240px]">
      <div className="flex items-center justify-between mb-0.5">
        <h4 className="text-xs font-bold text-gray-800 m-0">{legend.title}</h4>
        <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded-full text-[9px] font-semibold">Satellite</span>
      </div>
      <div className="text-[10px] text-gray-500 mb-2">{legend.unit}</div>
      
      {/* Color gradient bar */}
      <div className="relative mb-1.5">
        <div
          className="h-4 rounded overflow-hidden"
          style={{
            background: `linear-gradient(to right, ${legend.colors.join(', ')})`,
          }}
        >
          <div className="absolute inset-0 border-2 border-white/30 rounded-lg pointer-events-none" />
        </div>
        
        {/* Value labels */}
        <div className="relative mt-0.5 h-4">
          {legend.labels.map((label, idx) => (
            <span
              key={idx}
              className="absolute text-[9px] font-medium text-gray-600 transform -translate-x-1/2"
              style={{
                left: `${(idx / (legend.labels.length - 1)) * 100}%`,
              }}
            >
              {label}
            </span>
          ))}
        </div>
      </div>
      
      {/* Data source */}
      <div className="mt-2 pt-2 border-t border-gray-200 flex items-center justify-between">
        <span className="text-[9px] text-gray-500">Sentinel-5P</span>
        <span className="text-[9px] text-purple-600 font-semibold">7-day avg</span>
      </div>
    </div>
  );
}

export default SatelliteLegend;
