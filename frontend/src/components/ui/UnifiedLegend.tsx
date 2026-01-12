/**
 * UnifiedLegend Component
 * 
 * Compact horizontal legend at bottom center showing all active map layers.
 * Consolidates satellite, GEE exposure, and other layer legends into one component.
 */

import { motion, AnimatePresence } from 'framer-motion';
import type { GEEPollutant } from '@/hooks/queries';

// =============================================================================
// Types
// =============================================================================

export interface UnifiedLegendProps {
  /** Satellite layer info */
  satellite?: {
    pollutant: GEEPollutant;
    visible: boolean;
  };
  /** GEE Exposure layer info */
  geeExposure?: {
    mode: 'exposure' | 'aqi';
    visible: boolean;
  };
  /** Ground stations visible */
  groundStations?: boolean;
}

// =============================================================================
// Legend Configurations
// =============================================================================

const SATELLITE_LEGENDS: Record<GEEPollutant, {
  title: string;
  unit: string;
  colors: string[];
  labels: string[];
}> = {
  NO2: {
    title: 'NO₂',
    unit: 'mol/m²',
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000', '#800000'],
    labels: ['Low', 'High'],
  },
  SO2: {
    title: 'SO₂',
    unit: 'mol/m²',
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['Low', 'High'],
  },
  CO: {
    title: 'CO',
    unit: 'mol/m²',
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['Low', 'High'],
  },
  O3: {
    title: 'O₃',
    unit: 'mol/m²',
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['Low', 'High'],
  },
  HCHO: {
    title: 'HCHO',
    unit: 'mol/m²',
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['Low', 'High'],
  },
  CH4: {
    title: 'CH₄',
    unit: 'ppb',
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['Low', 'High'],
  },
  AER_AI: {
    title: 'Aerosol',
    unit: 'index',
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['Low', 'High'],
  },
  CLOUD: {
    title: 'Cloud',
    unit: 'fraction',
    colors: ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF8000', '#FF0000'],
    labels: ['0', '1'],
  },
};

const EXPOSURE_LEGEND = {
  title: 'Exposure Index',
  colors: ['#00FF00', '#FFFF00', '#FFA500', '#FF0000', '#800080', '#400020'],
  labels: ['Low', 'High'],
};

const AQI_LEGEND = {
  title: 'AQI',
  colors: ['#00E400', '#FFFF00', '#FF7E00', '#FF0000', '#8F3F97', '#7E0023'],
  labels: ['Good', 'Moderate', 'Unhealthy FSG', 'Unhealthy', 'Very Unhealthy', 'Hazardous'],
};

// =============================================================================
// Component
// =============================================================================

export function UnifiedLegend({
  satellite,
  geeExposure,
  groundStations = false,
}: UnifiedLegendProps) {
  
  const activeLegends = [];
  
  // Add satellite legend if visible
  if (satellite?.visible && satellite.pollutant) {
    const config = SATELLITE_LEGENDS[satellite.pollutant];
    if (config) {
      activeLegends.push({
        id: 'satellite',
        title: config.title,
        subtitle: config.unit,
        colors: config.colors,
        labels: config.labels,
      });
    }
  }
  
  // Add GEE exposure/AQI legend if visible
  if (geeExposure?.visible) {
    const config = geeExposure.mode === 'aqi' ? AQI_LEGEND : EXPOSURE_LEGEND;
    activeLegends.push({
      id: 'gee-exposure',
      title: config.title,
      subtitle: geeExposure.mode === 'aqi' ? 'Air Quality Index' : 'Population × AQI',
      colors: config.colors,
      labels: config.labels,
    });
  }
  
  // Add ground stations legend if visible
  if (groundStations) {
    activeLegends.push({
      id: 'ground',
      title: 'Ground Stations',
      subtitle: 'Real-time monitors',
      colors: null, // Special case for markers
      labels: null,
    });
  }
  
  // Don't render if no active legends
  if (activeLegends.length === 0) {
    return null;
  }
  
  return (
    <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-20 pointer-events-none">
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          transition={{ duration: 0.3 }}
          className="bg-white/95 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200 pointer-events-auto"
        >
          <div className="flex items-center gap-6 px-4 py-2">
            {activeLegends.map((legend, idx) => (
              <div key={legend.id} className="flex items-center gap-3">
                {/* Separator */}
                {idx > 0 && (
                  <div className="w-px h-8 bg-gray-300" />
                )}
                
                {/* Legend content */}
                <div className="flex items-center gap-2">
                  {/* Title */}
                  <div className="text-sm">
                    <div className="font-semibold text-gray-800">{legend.title}</div>
                    {legend.subtitle && (
                      <div className="text-xs text-gray-500">{legend.subtitle}</div>
                    )}
                  </div>
                  
                  {/* Color gradient or markers */}
                  {legend.colors ? (
                    <div className="flex flex-col gap-1">
                      {/* Gradient bar */}
                      <div 
                        className="h-4 w-32 rounded"
                        style={{
                          background: `linear-gradient(to right, ${legend.colors.join(', ')})`,
                        }}
                      />
                      
                      {/* Labels */}
                      {legend.labels && (
                        <div className="flex justify-between text-[10px] text-gray-600">
                          {legend.labels.map((label, i) => (
                            <span key={i}>{label}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Ground station markers */
                    <div className="flex gap-2">
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-green-500 border-2 border-white shadow" />
                        <span className="text-xs text-gray-600">Good</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-yellow-500 border-2 border-white shadow" />
                        <span className="text-xs text-gray-600">Moderate</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-red-500 border-2 border-white shadow" />
                        <span className="text-xs text-gray-600">Unhealthy</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

export default UnifiedLegend;
