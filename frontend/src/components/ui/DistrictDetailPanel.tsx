/**
 * District Detail Panel
 * 
 * Shows comprehensive district-level stats when clicked on map.
 * Displays AQI, PM2.5, population exposure, trends, and risk data.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { X, AlertTriangle, Users, Wind, Satellite } from 'lucide-react';
import { useDistrictExposure, useExposureTrends } from '@/hooks/queries';
import type { DistrictExposureProperties } from '@/components/layers/DistrictsLayer';
import type { SatelliteExposureResponse } from '@/hooks/queries/useSatelliteExposure';

interface DistrictDetailPanelProps {
  district: DistrictExposureProperties | null;
  isOpen: boolean;
  onClose: () => void;
  satelliteExposure?: SatelliteExposureResponse;
  exposureLoading?: boolean;
}

export function DistrictDetailPanel({
  district,
  isOpen,
  onClose,
  satelliteExposure,
  exposureLoading,
}: DistrictDetailPanelProps) {
  if (!district) return null;

  // Fetch detailed district data (disabled - old exposure calculation)
  const { isLoading: detailLoading } = useDistrictExposure(
    district.district_id,
    { enabled: false } // Disabled: old exposure data
  );

  // Fetch trends (disabled - needs new calculation method)
  const { isLoading: trendsLoading } = useExposureTrends(
    { days: 30 },
    { enabled: false } // Disabled: old exposure data
  );

  // Get AQI category and color
  const getAQICategory = (aqi: number | null) => {
    if (!aqi) return 'Unknown';
    if (aqi <= 50) return 'Good';
    if (aqi <= 100) return 'Moderate';
    if (aqi <= 150) return 'Unhealthy for Sensitive Groups';
    if (aqi <= 200) return 'Unhealthy';
    if (aqi <= 300) return 'Very Unhealthy';
    return 'Hazardous';
  };

  const getAQIColor = (aqi: number | null) => {
    if (!aqi) return '#999999';
    if (aqi <= 50) return '#22C55E'; // Green
    if (aqi <= 100) return '#EAB308'; // Yellow
    if (aqi <= 150) return '#F97316'; // Orange
    if (aqi <= 200) return '#EF4444'; // Red
    if (aqi <= 300) return '#8B1E23'; // Dark Red
    return '#7E0023'; // Maroon
  };

  const panelVariants = {
    hidden: { x: 400, opacity: 0 },
    visible: {
      x: 0,
      opacity: 1,
      transition: { duration: 0.3 },
    },
    exit: {
      x: 400,
      opacity: 0,
      transition: { duration: 0.2 },
    },
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-30"
          />

          {/* Panel */}
          <motion.div
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed right-0 top-0 bottom-0 w-80 bg-white/95 backdrop-blur-xl border-l border-gray-200 shadow-2xl z-40 overflow-y-auto"
          >
            {/* Header */}
            <div className="sticky top-0 bg-white/98 backdrop-blur-xl border-b border-gray-200 p-3 flex items-start justify-between">
              <div className="flex-1">
                <h2 className="text-lg font-bold text-gray-900">
                  {district.district_name}
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {district.province}
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                title="Close panel"
              >
                <X size={18} className="text-gray-600" />
              </button>
            </div>

            {/* Content */}
            <div className="p-3 space-y-4">
              {/* AQI Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-gradient-to-br from-blue-50/80 to-indigo-50/80 rounded-xl p-3 border border-gray-200 shadow-sm"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-xs font-semibold text-gray-700">Air Quality Index</h3>
                  <Wind size={14} className="text-gray-500" />
                </div>

                <div className="flex items-end gap-3">
                  <div>
                    <div
                      className="text-4xl font-bold transition-colors"
                      style={{ color: getAQIColor(district.mean_aqi) }}
                    >
                      {district.mean_aqi?.toFixed(0) ?? '—'}
                    </div>
                    <p className="text-[10px] text-gray-600 mt-0.5">
                      {getAQICategory(district.mean_aqi)}
                    </p>
                  </div>

                  <div className="flex-1">
                    <p className="text-[10px] text-gray-500 mb-1">PM2.5</p>
                    <p className="text-xl font-semibold text-gray-800">
                      {district.mean_pm25?.toFixed(1) ?? '—'} μg/m³
                    </p>
                  </div>
                </div>

                <div className="mt-2 pt-2 border-t border-gray-200 text-[10px] text-gray-500">
                  <p>{district.data_source} • {district.date}</p>
                </div>
              </motion.div>

              {/* Population Exposure */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-gradient-to-br from-green-50/80 to-emerald-50/80 rounded-xl p-3 border border-gray-200 shadow-sm"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Users size={14} className="text-green-600" />
                  <h3 className="text-xs font-semibold text-gray-700">Population Exposure</h3>
                </div>

                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between items-center mb-0.5">
                      <span className="text-[10px] text-gray-600">Total Population</span>
                      <span className="text-sm font-semibold text-gray-800">
                        {district.total_population
                          ? (district.total_population / 1_000_000).toFixed(1) + 'M'
                          : '—'}
                      </span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[10px] text-gray-600">At Risk</span>
                      <span className="text-sm font-semibold text-red-600">
                        {district.pop_at_risk
                          ? (district.pop_at_risk / 1_000_000).toFixed(2) + 'M'
                          : '—'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-gradient-to-r from-yellow-500 to-red-500 h-1.5 rounded-full transition-all"
                        style={{
                          width: `${
                            district.total_population && district.pop_at_risk
                              ? (district.pop_at_risk / district.total_population) * 100
                              : 0
                          }%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* AQI Breakdown */}
                  <div className="pt-2 border-t border-white/10 space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-green-400">Good</span>
                      <span className="text-muted-foreground">
                        {district.pop_good ? (district.pop_good / 1_000_000).toFixed(1) + 'M' : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-yellow-400">Moderate</span>
                      <span className="text-muted-foreground">
                        {district.pop_moderate
                          ? (district.pop_moderate / 1_000_000).toFixed(1) + 'M'
                          : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-orange-400">Unhealthy</span>
                      <span className="text-muted-foreground">
                        {district.pop_unhealthy
                          ? (district.pop_unhealthy / 1_000_000).toFixed(1) + 'M'
                          : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-red-400">Very Unhealthy</span>
                      <span className="text-muted-foreground">
                        {district.pop_very_unhealthy
                          ? (district.pop_very_unhealthy / 1_000_000).toFixed(1) + 'M'
                          : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-rose-600">Hazardous</span>
                      <span className="text-muted-foreground">
                        {district.pop_hazardous
                          ? (district.pop_hazardous / 1_000_000).toFixed(1) + 'M'
                          : '—'}
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Exposure Index */}
              {district.exposure_index !== null && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="bg-gradient-to-br from-white/5 to-white/10 rounded-xl p-4 border border-white/20"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle size={16} className="text-tech-blue-400" />
                    <h3 className="text-sm font-semibold text-foreground">Exposure Index</h3>
                  </div>
                  <p className="text-3xl font-bold text-tech-blue-400">
                    {district.exposure_index.toFixed(2)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    Integrated population exposure metric
                  </p>
                </motion.div>
              )}

              {/* Satellite Exposure Data - 5km Radius */}
              {satelliteExposure && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-xl p-4 border border-cyan-500/30"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <Satellite size={16} className="text-cyan-400" />
                    <h3 className="text-sm font-semibold text-foreground">Satellite Exposure (5km Radius)</h3>
                  </div>

                  <div className="space-y-3">
                    {/* Mean AQI */}
                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs text-muted-foreground">Mean AQI (Satellite)</span>
                        <span className="text-sm font-semibold text-cyan-400">
                          {satelliteExposure.exposure?.mean_aqi?.toFixed(0) ?? '—'}
                        </span>
                      </div>
                    </div>

                    {/* Mean PM2.5 */}
                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs text-muted-foreground">Mean PM2.5</span>
                        <span className="text-sm font-semibold text-cyan-400">
                          {satelliteExposure.exposure?.mean_pm25?.toFixed(1) ?? '—'} μg/m³
                        </span>
                      </div>
                    </div>

                    {/* Population at Risk (Satellite) */}
                    {satelliteExposure.exposure?.pop_at_risk !== null && (
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs text-muted-foreground">Pop. at Risk</span>
                          <span className="text-sm font-semibold text-cyan-400">
                            {(satelliteExposure.exposure.pop_at_risk / 1_000_000).toFixed(2)}M
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Exposure Index (Satellite) */}
                    {satelliteExposure.exposure?.exposure_index !== null && (
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs text-muted-foreground">Exposure Index</span>
                          <span className="text-sm font-semibold text-cyan-400">
                            {satelliteExposure.exposure.exposure_index.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Data Source and Date */}
                    <div className="pt-2 border-t border-white/10 text-xs text-muted-foreground">
                      <p>Source: {satelliteExposure.exposure?.data_source}</p>
                      <p>Date: {new Date(satelliteExposure.target_date).toLocaleDateString()}</p>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Loading State */}
              {(detailLoading || trendsLoading || exposureLoading) && (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-tech-blue-400" />
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export default DistrictDetailPanel;
