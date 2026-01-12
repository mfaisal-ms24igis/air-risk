/**
 * GEE Exposure Analysis Page
 * 
 * Dedicated page for calculating and visualizing pixel-based exposure analysis
 * using Google Earth Engine Sentinel-5P data.
 * 
 * @module pages/ExposureAnalysisPage
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { MapBase, MAP_STYLES } from '@/components/map';
import type { Map as MapLibreMap } from 'maplibre-gl';
import { GEEExposureLayer } from '@/components/layers';
import { queryKeys } from '@/lib/query-client';
import { getDistricts } from '@/api/districts';
import { calculateDistrictExposure } from '@/api/geeExposure';
import type { GEEExposureResult } from '@/api/geeExposure';
import { ChevronLeft, Calculator, MapPin, Calendar, Loader2, Info } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function ExposureAnalysisPage() {
  const navigate = useNavigate();
  const mapRef = useRef<MapLibreMap | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<number | undefined>();
  const [daysBack, setDaysBack] = useState(7);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exposureResult, setExposureResult] = useState<GEEExposureResult | null>(null);
  const [displayMode, setDisplayMode] = useState<'exposure' | 'aqi'>('exposure');

  // Fetch districts
  const { data: districtsData, isLoading: districtsLoading, error: districtsError } = useQuery({
    queryKey: queryKeys.geojson.districts(),
    queryFn: async () => {
      console.log('[ExposureAnalysisPage] Fetching districts...');
      try {
        const result = await getDistricts();
        console.log('[ExposureAnalysisPage] Districts fetched:', result);
        return result;
      } catch (err) {
        console.error('[ExposureAnalysisPage] Districts fetch error:', err);
        throw err;
      }
    },
    retry: 2,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
  const districts = districtsData || [];

  // Zoom to district
  const zoomToDistrict = useCallback((districtId: number) => {
    if (!mapRef.current) return;
    
    const district = districts.find(d => d.id === districtId);
    if (!district?.geometry) {
      console.warn('[ExposureAnalysisPage] No geometry found for district:', districtId);
      return;
    }
    
    // Calculate bounds from geometry
    let coords: number[][];
    try {
      if (district.geometry.type === 'Polygon') {
        coords = district.geometry.coordinates[0];
      } else if (district.geometry.type === 'MultiPolygon') {
        coords = district.geometry.coordinates[0][0];
      } else {
        console.warn('[ExposureAnalysisPage] Unsupported geometry type:', district.geometry.type);
        return;
      }
      
      if (!coords || !Array.isArray(coords) || coords.length === 0) {
        console.warn('[ExposureAnalysisPage] Invalid coordinates for district:', districtId);
        return;
      }
    } catch (error) {
      console.error('[ExposureAnalysisPage] Error accessing geometry coordinates:', error);
      return;
    }
    
    let minLng = Infinity, minLat = Infinity;
    let maxLng = -Infinity, maxLat = -Infinity;
    
    coords.forEach(([lng, lat]: [number, number]) => {
      minLng = Math.min(minLng, lng);
      minLat = Math.min(minLat, lat);
      maxLng = Math.max(maxLng, lng);
      maxLat = Math.max(maxLat, lat);
    });
    
    mapRef.current.fitBounds(
      [[minLng, minLat], [maxLng, maxLat]],
      { padding: 80, duration: 1000 }
    );
  }, [districts]);

  // Zoom to district when selected
  useEffect(() => {
    if (selectedDistrict && districts.length > 0) {
      zoomToDistrict(selectedDistrict);
    }
  }, [selectedDistrict, districts, zoomToDistrict]);

  // Calculate exposure
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
        undefined,
        daysBack
      );
      setExposureResult(result);
      
      // Zoom to exposure data bounds
      if (mapRef.current && result.geometry_bounds) {
        const { west, south, east, north } = result.geometry_bounds;
        mapRef.current.fitBounds(
          [[west, south], [east, north]],
          { padding: 80, duration: 1500 }
        );
      }
    } catch (err) {
      console.error('[ExposureAnalysisPage] Calculation error:', err);
      setError(err instanceof Error ? err.message : 'Failed to calculate exposure');
    } finally {
      setIsCalculating(false);
    }
  }, [selectedDistrict, daysBack]);

  const selectedDistrictName = districts.find(d => d.id === selectedDistrict)?.name;

  return (
    <div className="fixed inset-0 flex bg-slate-950">
      {/* Left Sidebar - Controls */}
      <motion.div
        initial={{ x: -400 }}
        animate={{ x: 0 }}
        className="w-96 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 border-r border-white/10 flex flex-col"
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <button
            onClick={() => navigate('/map')}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="text-sm">Back to Map</span>
          </button>
          <h1 className="text-2xl font-bold text-white mb-2">Exposure Analysis</h1>
          <p className="text-sm text-gray-400">
            Calculate pixel-based air quality exposure using GEE Sentinel-5P data
          </p>
        </div>

        {/* Controls */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* District Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <MapPin className="w-4 h-4 inline mr-2" />
              Select District
            </label>
            {districtsLoading ? (
              <div className="bg-white/5 rounded-lg p-4 text-center text-gray-400">
                <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                Loading districts...
              </div>
            ) : districtsError ? (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-300 text-sm">
                <p className="font-semibold mb-1">Failed to load districts</p>
                <p className="text-xs text-red-400">{String(districtsError)}</p>
              </div>
            ) : districts.length === 0 ? (
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 text-yellow-300 text-sm">
                No districts available. Please check your authentication.
              </div>
            ) : (
              <select
                value={selectedDistrict || ''}
                onChange={(e) => setSelectedDistrict(Number(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              >
                <option value="">Choose a district...</option>
                {districts.map(district => (
                  <option key={district.id} value={district.id}>
                    {district.name} ({district.province})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Days Back Slider */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Calendar className="w-4 h-4 inline mr-2" />
              Averaging Period: {daysBack} days
            </label>
            <input
              type="range"
              min="1"
              max="30"
              value={daysBack}
              onChange={(e) => setDaysBack(Number(e.target.value))}
              className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1 day</span>
              <span>30 days</span>
            </div>
          </div>

          {/* Display Mode Toggle */}
          {exposureResult && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Display Mode
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setDisplayMode('exposure')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${displayMode === 'exposure'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                    }`}
                >
                  Exposure Score
                </button>
                <button
                  onClick={() => setDisplayMode('aqi')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${displayMode === 'aqi'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                    }`}
                >
                  AQI
                </button>
              </div>
            </div>
          )}

          {/* Calculate Button */}
          <button
            onClick={handleCalculate}
            disabled={!selectedDistrict || isCalculating}
            className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 disabled:from-gray-600 disabled:to-gray-600 text-white font-medium py-3 rounded-lg transition-all shadow-lg disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isCalculating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Calculator className="w-5 h-5" />
                Calculate Exposure
              </>
            )}
          </button>
          
          {/* Calculation Status */}
          {isCalculating && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-blue-300 text-xs"
            >
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 flex-shrink-0 mt-0.5 animate-pulse" />
                <div>
                  <div className="font-semibold mb-1">Processing GEE Data</div>
                  <div className="text-blue-200/80 space-y-1">
                    <div>• Fetching Sentinel-5P satellite data...</div>
                    <div>• Calculating AQI and exposure indices...</div>
                    <div>• Generating visualization tiles...</div>
                    <div className="text-blue-300/60 mt-2">This may take 30-60 seconds</div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Error Display */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-300 text-sm">
              {error}
            </div>
          )}

          {/* Results Summary */}
          {exposureResult && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white/5 border border-white/10 rounded-lg p-4 space-y-3"
            >
              <h3 className="text-sm font-semibold text-white mb-2">
                Results: {selectedDistrictName}
              </h3>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Population Exposed:</span>
                  <span className="text-white font-medium">
                    {exposureResult.statistics.total_population.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Mean AQI:</span>
                  <span className="text-white font-medium">
                    {exposureResult.statistics.mean_aqi.toFixed(1)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Max AQI:</span>
                  <span className="text-white font-medium">
                    {exposureResult.statistics.max_aqi.toFixed(1)}
                  </span>
                </div>
              </div>

              <div className="pt-3 border-t border-white/10">
                <div className="text-xs text-gray-400 mb-2">Pollutant Concentrations:</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <div className="text-gray-500">NO2</div>
                    <div className="text-white">{(exposureResult.statistics.pollutants.no2 || 0).toFixed(2)} ppb</div>
                  </div>
                  <div>
                    <div className="text-gray-500">SO2</div>
                    <div className="text-white">{(exposureResult.statistics.pollutants.so2 || 0).toFixed(2)} ppb</div>
                  </div>
                  <div>
                    <div className="text-gray-500">CO</div>
                    <div className="text-white">{(exposureResult.statistics.pollutants.co || 0).toFixed(2)} ppm</div>
                  </div>
                  <div>
                    <div className="text-gray-500">PM2.5</div>
                    <div className="text-white">{(exposureResult.statistics.pollutants.pm25 || 0).toFixed(2)} µg/m³</div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Info Box */}
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-blue-300 text-xs space-y-2">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold mb-1">About This Analysis</div>
                <ul className="space-y-1 text-blue-200/80">
                  <li>• Uses Sentinel-5P satellite data (1113m resolution)</li>
                  <li>• Calculates pixel-based exposure with population weighting</li>
                  <li>• EPA AQI calculated on Google Earth Engine</li>
                  <li>• PM2.5 estimated from NO2 correlation</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Right Side - Map */}
      <div className="flex-1 relative">
        <MapBase
          style={MAP_STYLES.CARTO_LIGHT}
          center={[69.3451, 30.3753]}
          zoom={6}
          containerStyle={{ width: '100%', height: '100%' }}
          onLoad={(map) => { mapRef.current = map; }}
        >
          {/* District Boundary */}
          {selectedDistrict && districts.length > 0 && (() => {
            const district = districts.find(d => d.id === selectedDistrict);
            if (!district?.geometry) return null;
            
            return (
              <>
                <source
                  id="district-boundary"
                  type="geojson"
                  data={{
                    type: 'Feature',
                    properties: { name: district.name },
                    geometry: district.geometry
                  }}
                />
                <layer
                  id="district-boundary-fill"
                  type="fill"
                  source="district-boundary"
                  paint={{
                    'fill-color': '#3b82f6',
                    'fill-opacity': 0.05
                  }}
                />
                <layer
                  id="district-boundary-line"
                  type="line"
                  source="district-boundary"
                  paint={{
                    'line-color': '#3b82f6',
                    'line-width': 3,
                    'line-opacity': 0.8
                  }}
                />
              </>
            );
          })()}
          
          {exposureResult && (
            <GEEExposureLayer
              exposureResult={exposureResult}
              mode={displayMode}
              visible={true}
              opacity={0.7}
            />
          )}
        </MapBase>

        {/* Map Legend */}
        {exposureResult && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute bottom-6 right-6 bg-white/95 backdrop-blur-xl rounded-lg shadow-2xl border border-gray-200 p-4 max-w-xs"
          >
            <h4 className="text-sm font-bold text-gray-800 mb-3">
              {displayMode === 'exposure' ? 'Exposure Score' : 'Air Quality Index'}
            </h4>
            <div className="space-y-2 text-xs">
              {displayMode === 'aqi' ? (
                <>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-green-500"></div>
                    <span className="text-gray-700">Good (0-50)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-yellow-500"></div>
                    <span className="text-gray-700">Moderate (51-100)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-orange-500"></div>
                    <span className="text-gray-700">Unhealthy (101-150)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-red-500"></div>
                    <span className="text-gray-700">Very Unhealthy (151-200)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-purple-600"></div>
                    <span className="text-gray-700">Hazardous (200+)</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-blue-400"></div>
                    <span className="text-gray-700">Low Exposure</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-yellow-400"></div>
                    <span className="text-gray-700">Moderate Exposure</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-orange-500"></div>
                    <span className="text-gray-700">High Exposure</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded bg-red-600"></div>
                    <span className="text-gray-700">Very High Exposure</span>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
