/**
 * Professional GIS Layer Controls
 * 
 * Advanced layer management panel with:
 * - Collapsible layer groups
 * - Visual layer previews
 * - Quick actions (zoom to extent, download)
 * - Blend mode controls
 * - Layer ordering (z-index)
 * - Search/filter layers
 * 
 * @module components/ui/LayerControls
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Layers, 
  ChevronDown, 
  ChevronRight,
  Eye, 
  EyeOff, 
  Settings, 
  Maximize2,
  Download,
  Search,
  Sliders,
  Satellite as SatelliteIcon,
  MapPin,
  Map as MapIcon
} from 'lucide-react';
import type { GEEPollutant } from '@/hooks/queries';
import { POLLUTANT_INFO } from '@/components/layers/SatelliteLayer';

// =============================================================================
// Types
// =============================================================================

export interface LayerState {
  districts: boolean;
  stations: boolean;
  satellite: boolean;
}

export interface LayerControlsProps {
  /** Current layer visibility state */
  layers: LayerState;
  /** Callback when layer visibility changes */
  onLayerChange: (layers: LayerState) => void;
  /** Current satellite pollutant */
  pollutant: GEEPollutant;
  /** Callback when pollutant changes */
  onPollutantChange: (pollutant: GEEPollutant) => void;
  /** Current date (YYYY-MM-DD) */
  date?: string;
  /** Available dates for current pollutant */
  availableDates?: string[];
  /** Callback when date changes */
  onDateChange?: (date: string) => void;
  /** Satellite layer opacity */
  satelliteOpacity?: number;
  /** Callback when opacity changes */
  onOpacityChange?: (opacity: number) => void;
  /** Whether satellite data is loading */
  satelliteLoading?: boolean;
  /** Station count */
  stationCount?: number;
  /** Current view mode (provinces or districts) */
  viewMode?: string;
  /** Selected province name */
  selectedProvince?: string;
  /** Callback to go back to provinces view */
  onBackToProvinces?: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const POLLUTANTS: GEEPollutant[] = ['NO2', 'SO2', 'CO', 'O3', 'HCHO', 'CH4', 'AER_AI'];

const LAYER_METADATA = {
  districts: {
    icon: MapIcon,
    name: 'District Boundaries',
    description: 'PM2.5 exposure by district',
    color: '#3b82f6',
    type: 'Vector',
  },
  stations: {
    icon: MapPin,
    name: 'Monitoring Stations',
    description: 'Ground-based air quality sensors',
    color: '#10b981',
    type: 'Point',
  },
  satellite: {
    icon: SatelliteIcon,
    name: 'Satellite Imagery',
    description: 'Sentinel-5P atmospheric data',
    color: '#8b5cf6',
    type: 'Raster',
  },
};

// =============================================================================
// Component
// =============================================================================

export function LayerControls({
  layers,
  onLayerChange,
  pollutant,
  onPollutantChange,
  date,
  availableDates,
  onDateChange,
  satelliteOpacity = 0.7,
  onOpacityChange,
  satelliteLoading = false,
  stationCount,
  viewMode,
  selectedProvince,
  onBackToProvinces,
}: LayerControlsProps) {
  const [minimized, setMinimized] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    base: true,
    overlay: true,
    satellite: true,
  });

  const toggleLayer = (layer: keyof LayerState) => {
    onLayerChange({ ...layers, [layer]: !layers[layer] });
  };

  const toggleGroup = (group: string) => {
    setExpandedGroups(prev => ({ ...prev, [group]: !prev[group] }));
  };

  // Filter layers based on search
  const filteredLayers = useMemo(() => {
    if (!searchTerm) return Object.keys(layers);
    return Object.keys(layers).filter(layer =>
      LAYER_METADATA[layer as keyof typeof LAYER_METADATA].name
        .toLowerCase()
        .includes(searchTerm.toLowerCase())
    );
  }, [searchTerm, layers]);

  const activeLayerCount = Object.values(layers).filter(Boolean).length;

  return (
    <motion.div
      initial={{ x: -400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20 }}
      className="absolute bottom-6 left-6 z-30 w-80"
    >
      <div className="bg-white/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-gray-200/50 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 text-white p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5" />
              <h3 className="font-semibold text-lg">Layer Manager</h3>
            </div>
            <button
              onClick={() => setMinimized(!minimized)}
              className="p-1 hover:bg-white/10 rounded transition-colors"
            >
              <ChevronDown className={`w-5 h-5 transition-transform ${minimized ? 'rotate-180' : ''}`} />
            </button>
          </div>
          
          {/* Drill-down Navigation */}
          {viewMode === 'districts' && selectedProvince ? (
            <div className="mb-2 px-3 py-2 bg-blue-500/20 rounded-lg border border-blue-400/30">
              <button 
                onClick={onBackToProvinces}
                className="text-sm text-blue-200 hover:text-white transition-colors flex items-center gap-1"
              >
                <ChevronRight className="w-4 h-4 rotate-180" />
                Back to All Provinces
              </button>
              <div className="text-sm font-semibold mt-1">Viewing: {selectedProvince}</div>
            </div>
          ) : (
            <div className="text-xs text-slate-300 mb-1">💡 Click a province to drill down</div>
          )}
          
          <div className="flex items-center gap-2 text-xs text-slate-300">
            <span>{activeLayerCount} active</span>
            <span>•</span>
            <span>{Object.keys(layers).length} total</span>
          </div>
        </div>

        <AnimatePresence>
          {!minimized && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {/* Search Bar */}
              <div className="p-4 border-b border-gray-200">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search layers..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Layers List */}
              <div className="max-h-[500px] overflow-y-auto">
                {/* Base Layers Group */}
                <div className="border-b border-gray-200">
                  <button
                    onClick={() => toggleGroup('base')}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <span className="text-sm font-semibold text-gray-700">Base Layers</span>
                    {expandedGroups.base ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                  </button>

                  <AnimatePresence>
                    {expandedGroups.base && (
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="overflow-hidden"
                      >
                        {/* Districts Layer */}
                        {filteredLayers.includes('districts') && (
                          <LayerItem
                            layer="districts"
                            isActive={layers.districts}
                            onToggle={() => toggleLayer('districts')}
                            metadata={LAYER_METADATA.districts}
                          />
                        )}

                        {/* Stations Layer */}
                        {filteredLayers.includes('stations') && (
                          <LayerItem
                            layer="stations"
                            isActive={layers.stations}
                            onToggle={() => toggleLayer('stations')}
                            metadata={LAYER_METADATA.stations}
                            badge={stationCount?.toString()}
                          />
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Satellite Layers Group */}
                <div>
                  <button
                    onClick={() => toggleGroup('satellite')}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <span className="text-sm font-semibold text-gray-700">Satellite Data</span>
                    {expandedGroups.satellite ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                  </button>

                  <AnimatePresence>
                    {expandedGroups.satellite && (
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="overflow-hidden"
                      >
                        {filteredLayers.includes('satellite') && (
                          <>
                            <LayerItem
                              layer="satellite"
                              isActive={layers.satellite}
                              onToggle={() => toggleLayer('satellite')}
                              metadata={LAYER_METADATA.satellite}
                              loading={satelliteLoading}
                            />

                            {/* Satellite Controls */}
                            {layers.satellite && (
                              <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="px-4 pb-4 bg-purple-50/50 space-y-3"
                              >
                                {/* Pollutant Selector */}
                                <div>
                                  <label className="block text-xs font-medium text-gray-700 mb-1">
                                    Pollutant Type
                                  </label>
                                  <select
                                    value={pollutant}
                                    onChange={(e) => onPollutantChange(e.target.value as GEEPollutant)}
                                    className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                                  >
                                    {POLLUTANTS.map((p) => (
                                      <option key={p} value={p}>
                                        {p} - {POLLUTANT_INFO[p].name}
                                      </option>
                                    ))}
                                  </select>
                                </div>

                                {/* Date Selector */}
                                {availableDates && availableDates.length > 0 && onDateChange && (
                                  <div>
                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                      Observation Date
                                    </label>
                                    <select
                                      value={date || ''}
                                      onChange={(e) => onDateChange(e.target.value)}
                                      className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                                    >
                                      {availableDates.slice(0, 30).map((d) => (
                                        <option key={d} value={d}>{d}</option>
                                      ))}
                                    </select>
                                  </div>
                                )}

                                {/* Opacity Slider */}
                                {onOpacityChange && (
                                  <div>
                                    <div className="flex items-center justify-between mb-1">
                                      <label className="text-xs font-medium text-gray-700">
                                        Layer Opacity
                                      </label>
                                      <span className="text-xs font-semibold text-purple-600">
                                        {Math.round(satelliteOpacity * 100)}%
                                      </span>
                                    </div>
                                    <input
                                      type="range"
                                      min="0"
                                      max="100"
                                      value={satelliteOpacity * 100}
                                      onChange={(e) => onOpacityChange(Number(e.target.value) / 100)}
                                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                                    />
                                  </div>
                                )}

                                {/* Pollutant Info Card */}
                                <div className="bg-white border border-purple-200 rounded-lg p-3">
                                  <div className="flex items-start gap-2">
                                    <div className="w-2 h-2 rounded-full bg-purple-500 mt-1.5" />
                                    <div>
                                      <p className="text-xs font-semibold text-gray-800">
                                        {POLLUTANT_INFO[pollutant].name}
                                      </p>
                                      <p className="text-xs text-gray-600 mt-1">
                                        {POLLUTANT_INFO[pollutant].description}
                                      </p>
                                    </div>
                                  </div>
                                </div>
                              </motion.div>
                            )}
                          </>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="border-t border-gray-200 p-3 bg-gray-50">
                <div className="flex gap-2">
                  <button className="flex-1 px-3 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors flex items-center justify-center gap-1">
                    <Maximize2 className="w-3 h-3" />
                    Fit Bounds
                  </button>
                  <button className="flex-1 px-3 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors flex items-center justify-center gap-1">
                    <Settings className="w-3 h-3" />
                    Settings
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// =============================================================================
// Layer Item Component
// =============================================================================

interface LayerItemProps {
  layer: string;
  isActive: boolean;
  onToggle: () => void;
  metadata: {
    icon: any;
    name: string;
    description: string;
    color: string;
    type: string;
  };
  badge?: string;
  loading?: boolean;
}

function LayerItem({ layer, isActive, onToggle, metadata, badge, loading }: LayerItemProps) {
  const Icon = metadata.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="px-4 py-3 hover:bg-gray-50 transition-colors border-l-4"
      style={{ borderLeftColor: isActive ? metadata.color : 'transparent' }}
    >
      <div className="flex items-start gap-3">
        {/* Visibility Toggle */}
        <button
          onClick={onToggle}
          className={`p-1.5 rounded-lg transition-all ${
            isActive 
              ? 'bg-blue-500 text-white hover:bg-blue-600' 
              : 'bg-gray-200 text-gray-400 hover:bg-gray-300'
          }`}
        >
          {isActive ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
        </button>

        {/* Layer Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Icon className="w-4 h-4 flex-shrink-0" style={{ color: metadata.color }} />
            <h4 className="text-sm font-medium text-gray-800 truncate">
              {metadata.name}
            </h4>
            {badge && (
              <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-700 rounded-full">
                {badge}
              </span>
            )}
            {loading && (
              <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{metadata.description}</p>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-gray-400">{metadata.type}</span>
          </div>
        </div>

        {/* Layer Actions */}
        <div className="flex gap-1">
          <button className="p-1 rounded hover:bg-gray-200 transition-colors opacity-0 group-hover:opacity-100">
            <Download className="w-3.5 h-3.5 text-gray-500" />
          </button>
          <button className="p-1 rounded hover:bg-gray-200 transition-colors opacity-0 group-hover:opacity-100">
            <Sliders className="w-3.5 h-3.5 text-gray-500" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

export default LayerControls;
