/**
 * Premium Exposure Control Panel
 * 
 * Control panel for GEE-based pixel-wise exposure visualization.
 * Premium feature with district selection and calculation triggers.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Crown, 
  MapPin, 
  Loader2, 
  Eye, 
  EyeOff, 
  Layers, 
  Calendar,
  ChevronDown,
  Sparkles,
  BarChart3
} from 'lucide-react';
import { calculateDistrictExposure, type GEEExposureResult } from '@/api/geeExposure';

export interface PremiumExposureControlProps {
  /** Available districts for selection */
  districts: Array<{ id: number; name: string; province: string }>;
  /** Currently selected district ID */
  selectedDistrictId?: number;
  /** Callback when exposure is calculated */
  onExposureCalculated: (result: GEEExposureResult) => void;
  /** Current display mode */
  displayMode: 'exposure' | 'aqi';
  /** Callback when mode changes */
  onModeChange: (mode: 'exposure' | 'aqi') => void;
  /** Layer visibility */
  visible: boolean;
  /** Callback when visibility changes */
  onVisibilityChange: (visible: boolean) => void;
  /** Layer opacity (0-1) */
  opacity: number;
  /** Callback when opacity changes */
  onOpacityChange: (opacity: number) => void;
}

export function PremiumExposureControl({
  districts,
  selectedDistrictId,
  onExposureCalculated,
  displayMode,
  onModeChange,
  visible,
  onVisibilityChange,
  opacity,
  onOpacityChange,
}: PremiumExposureControlProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<number | undefined>(selectedDistrictId);
  const [daysBack, setDaysBack] = useState(7);

  // Handle district selection
  const handleDistrictSelect = useCallback((districtId: number) => {
    setSelectedDistrict(districtId);
    setError(null);
  }, []);

  // Calculate exposure for selected district
  const handleCalculate = useCallback(async () => {
    if (!selectedDistrict) {
      setError('Please select a district');
      return;
    }

    setIsCalculating(true);
    setError(null);

    try {
      const result = await calculateDistrictExposure(
        selectedDistrict,
        undefined, // Use latest date
        daysBack
      );

      onExposureCalculated(result);
      setIsExpanded(false); // Collapse after successful calculation
    } catch (err) {
      console.error('[PremiumExposureControl] Calculation error:', err);
      setError(err instanceof Error ? err.message : 'Failed to calculate exposure');
    } finally {
      setIsCalculating(false);
    }
  }, [selectedDistrict, daysBack, onExposureCalculated]);

  // Get selected district name
  const selectedDistrictName = districts.find(d => d.id === selectedDistrict)?.name;

  return (
    <motion.div
      initial={{ x: -400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20 }}
      className="absolute top-28 left-6 z-[950] w-80"
    >
      {/* Main control card */}
      <div className="bg-gradient-to-br from-amber-50 to-yellow-50 backdrop-blur-xl border-2 border-amber-300/50 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div
          className="bg-gradient-to-r from-amber-500 to-yellow-500 px-4 py-3 cursor-pointer select-none"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Crown className="w-5 h-5 text-white" />
              <h3 className="text-sm font-bold text-white">Premium Exposure</h3>
            </div>
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="w-5 h-5 text-white" />
            </motion.div>
          </div>
          <p className="text-xs text-amber-100 mt-1">Pixel-wise GEE Analysis</p>
        </div>

        {/* Expandable content */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="p-4 space-y-4">
                {/* District selector */}
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-2">
                    <MapPin className="inline w-3 h-3 mr-1" />
                    Select District
                  </label>
                  <select
                    value={selectedDistrict || ''}
                    onChange={(e) => handleDistrictSelect(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                    disabled={isCalculating}
                  >
                    <option value="">Choose a district...</option>
                    {districts.map((district) => (
                      <option key={district.id} value={district.id}>
                        {district.name} ({district.province})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Days back slider */}
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-2">
                    <Calendar className="inline w-3 h-3 mr-1" />
                    Average Period: {daysBack} days
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="30"
                    value={daysBack}
                    onChange={(e) => setDaysBack(Number(e.target.value))}
                    className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
                    disabled={isCalculating}
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>1 day</span>
                    <span>30 days</span>
                  </div>
                </div>

                {/* Calculate button */}
                <button
                  onClick={handleCalculate}
                  disabled={!selectedDistrict || isCalculating}
                  className="w-full bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 disabled:from-gray-300 disabled:to-gray-400 text-white font-bold py-3 px-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isCalculating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Calculating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Calculate Exposure
                    </>
                  )}
                </button>

                {/* Error message */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700"
                  >
                    {error}
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Quick controls (always visible) */}
        <div className="bg-white/80 backdrop-blur-sm border-t border-amber-200 p-3 space-y-3">
          {/* Display mode toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onModeChange('exposure')}
              className={`flex-1 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                displayMode === 'exposure'
                  ? 'bg-amber-500 text-white shadow-md'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <BarChart3 className="inline w-3 h-3 mr-1" />
              Exposure
            </button>
            <button
              onClick={() => onModeChange('aqi')}
              className={`flex-1 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                displayMode === 'aqi'
                  ? 'bg-amber-500 text-white shadow-md'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Layers className="inline w-3 h-3 mr-1" />
              AQI
            </button>
          </div>

          {/* Visibility toggle */}
          <button
            onClick={() => onVisibilityChange(!visible)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-700 transition-all"
          >
            <span>Layer Visibility</span>
            {visible ? (
              <Eye className="w-4 h-4 text-green-600" />
            ) : (
              <EyeOff className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {/* Opacity slider */}
          {visible && (
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">
                Opacity: {Math.round(opacity * 100)}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={opacity * 100}
                onChange={(e) => onOpacityChange(Number(e.target.value) / 100)}
                className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
              />
            </div>
          )}

          {/* Current selection info */}
          {selectedDistrictName && (
            <div className="text-xs text-gray-600 bg-amber-50 rounded-lg p-2 border border-amber-200">
              <strong className="text-amber-700">Active:</strong> {selectedDistrictName}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default PremiumExposureControl;
