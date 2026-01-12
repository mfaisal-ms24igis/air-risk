/**
 * Stations Page with OpenAQ Latest Readings
 * 
 * Browse air quality monitoring stations and view latest OpenAQ readings in JSON format.
 * @module pages/StationsPage
 */

import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, Loader, X, RefreshCw, Copy } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';

interface Station {
  id: number;
  name: string;
  data_source: string;
  openaq_location_id?: string;
  district?: string;
  province?: string;
  location: {
    lat: number;
    lng: number;
  };
  is_active: boolean;
  available_parameters?: string[];
}

interface StationDetail {
  id: number;
  name: string;
  data_source: string;
  openaq_location_id?: string;
  district?: {
    id: number;
    name: string;
    province: string;
  };
  location: {
    lat: number;
    lng: number;
  };
  is_active: boolean;
  available_parameters?: string[];
  latest_readings: Record<string, {
    timestamp: string;
    value: number;
    value_normalized: number;
    unit: string;
  }>;
  last_updated?: string;
}

async function fetchStations(): Promise<Station[]> {
  const response = await apiClient.get('/air-quality/stations/');
  return response as any;
}

async function fetchStationDetail(stationId: number, refresh: boolean = false): Promise<StationDetail> {
  const url = refresh 
    ? `/air-quality/stations/${stationId}/?refresh=true`
    : `/air-quality/stations/${stationId}/`;
  const response = await apiClient.get(url);
  return response as any;
}

// Helper to check if station has recent data (within last 24 hours)
function hasRecentData(station: StationDetail): boolean {
  if (!station.latest_readings || Object.keys(station.latest_readings).length === 0) {
    return false;
  }
  
  const timestamps = Object.values(station.latest_readings).map(r => new Date(r.timestamp).getTime());
  const mostRecent = Math.max(...timestamps);
  const twentyFourHoursAgo = Date.now() - (24 * 60 * 60 * 1000);
  
  return mostRecent > twentyFourHoursAgo;
}

export default function StationsPage() {
  const [selectedStation, setSelectedStation] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProvince, setSelectedProvince] = useState('');
  const [stationsWithDetails, setStationsWithDetails] = useState<Map<number, StationDetail>>(new Map());

  // Fetch all stations
  const { data: stations = [], isLoading, error } = useQuery({
    queryKey: ['stations'],
    queryFn: fetchStations,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch selected station details
  const { 
    data: stationDetail, 
    isLoading: isLoadingDetail, 
    refetch: refetchDetail 
  } = useQuery({
    queryKey: ['station-detail', selectedStation],
    queryFn: () => fetchStationDetail(selectedStation!, false),
    enabled: selectedStation !== null,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
  
  // Cache station details when fetched
  if (stationDetail && !stationsWithDetails.has(stationDetail.id)) {
    setStationsWithDetails(prev => new Map(prev).set(stationDetail.id, stationDetail));
  }
  
  // Force refresh from OpenAQ
  const handleForceRefresh = async () => {
    if (selectedStation) {
      await fetchStationDetail(selectedStation, true);
      refetchDetail();
    }
  };

  // Filter and sort stations
  const filteredStations = stations
    .filter(station => {
      const matchesSearch = searchQuery === '' || 
        station.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        station.district?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesProvince = selectedProvince === '' || station.province === selectedProvince;
      
      return matchesSearch && matchesProvince;
    })
    .sort((a, b) => {
      // Get details for both stations
      const aDetails = stationsWithDetails.get(a.id);
      const bDetails = stationsWithDetails.get(b.id);
      
      // 1. Prioritize stations with recent data (within 24 hours)
      const aHasRecent = aDetails ? hasRecentData(aDetails) : false;
      const bHasRecent = bDetails ? hasRecentData(bDetails) : false;
      
      if (aHasRecent && !bHasRecent) return -1;
      if (!aHasRecent && bHasRecent) return 1;
      
      // 2. Sort by number of readings (stations with more data first)
      const aReadingsCount = aDetails ? Object.keys(aDetails.latest_readings).length : 0;
      const bReadingsCount = bDetails ? Object.keys(bDetails.latest_readings).length : 0;
      
      if (aReadingsCount !== bReadingsCount) {
        return bReadingsCount - aReadingsCount; // Descending order
      }
      
      // 3. Sort by number of available parameters
      const aParamCount = a.available_parameters?.length || 0;
      const bParamCount = b.available_parameters?.length || 0;
      
      if (aParamCount !== bParamCount) {
        return bParamCount - aParamCount; // Descending order
      }
      
      // 4. Finally, sort alphabetically by name
      return a.name.localeCompare(b.name);
    });

  // Get unique provinces
  const provinces = Array.from(new Set(stations.map(s => s.province).filter(Boolean))) as string[];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 md:p-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-4xl font-bold text-white mb-2">Air Quality Stations</h1>
        <p className="text-gray-400">
          {isLoading ? 'Loading stations...' : `Monitoring ${stations.length} stations across Pakistan`}
        </p>
      </motion.div>

      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm"
        >
          Failed to load stations. Please refresh the page.
        </motion.div>
      )}

      {/* Search and Filter */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="mb-8 space-y-4"
      >
        <input
          type="text"
          placeholder="Search stations by name or district..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:border-blue-500/50 transition-all"
        />

        {provinces.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedProvince('')}
              className={`px-4 py-2 rounded-lg text-sm transition-all ${
                selectedProvince === ''
                  ? 'bg-blue-500/40 border border-blue-500 text-blue-300'
                  : 'bg-white/5 border border-white/10 text-gray-400 hover:border-blue-500/50'
              }`}
            >
              All Provinces
            </button>
            {provinces.map((province) => (
              <button
                key={province}
                onClick={() => setSelectedProvince(province)}
                className={`px-4 py-2 rounded-lg text-sm transition-all ${
                  selectedProvince === province
                    ? 'bg-blue-500/40 border border-blue-500 text-blue-300'
                    : 'bg-white/5 border border-white/10 text-gray-400 hover:border-blue-500/50'
                }`}
              >
                {province}
              </button>
            ))}
          </div>
        )}
      </motion.div>

      {/* Stations Table */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : filteredStations.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-400">No stations found matching your search.</p>
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10 bg-white/5">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">
                    Station Name
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">
                    Location
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">
                    Data Source
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">
                    Parameters
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">
                    Coordinates
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredStations.map((station, idx) => {
                  const stationDetails = stationsWithDetails.get(station.id);
                  const hasRecent = stationDetails ? hasRecentData(stationDetails) : false;
                  
                  return (
                    <motion.tr
                      key={station.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.02 }}
                      onClick={() => setSelectedStation(station.id)}
                      className={`border-b border-white/5 cursor-pointer transition-all hover:bg-blue-500/10 ${
                        hasRecent 
                          ? 'bg-green-500/10 hover:bg-green-500/20' 
                          : 'hover:bg-white/5'
                      }`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded-full ${
                            station.is_active ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                          }`}></div>
                          {hasRecent && (
                            <span className="text-xs px-2 py-0.5 bg-green-500/30 text-green-300 rounded font-medium">
                              Recent Data
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <MapPin className={`flex-shrink-0 ${hasRecent ? 'text-green-400' : 'text-blue-500'}`} size={16} />
                          <span className={`font-medium ${hasRecent ? 'text-green-300' : 'text-white'}`}>
                            {station.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-300">
                          {station.district && <div>{station.district}</div>}
                          {station.province && <div className="text-xs text-gray-400">{station.province}</div>}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm px-3 py-1 bg-white/10 rounded text-gray-300">
                          {station.data_source || 'Unknown'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {station.available_parameters && station.available_parameters.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {station.available_parameters.slice(0, 3).map(param => (
                              <span key={param} className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded">
                                {param.toUpperCase()}
                              </span>
                            ))}
                            {station.available_parameters.length > 3 && (
                              <span className="text-xs px-2 py-0.5 bg-gray-500/20 text-gray-400 rounded">
                                +{station.available_parameters.length - 3}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-gray-500">N/A</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-xs text-gray-400 font-mono">
                          {station.location.lat.toFixed(4)}, {station.location.lng.toFixed(4)}
                        </span>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* Station Detail Modal */}
      <AnimatePresence>
        {selectedStation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedStation(null)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-slate-900 border border-white/20 rounded-xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-white/10">
                <div>
                  <h2 className="text-2xl font-bold text-white">
                    {stationDetail?.name || 'Loading...'}
                  </h2>
                  {stationDetail?.district && (
                    <p className="text-gray-400 text-sm mt-1">
                      {stationDetail.district.name}, {stationDetail.district.province}
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleForceRefresh}
                    disabled={isLoadingDetail}
                    className="px-3 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/50 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2 text-sm text-blue-300"
                    title="Fetch latest data from OpenAQ"
                  >
                    <RefreshCw className={`w-4 h-4 ${isLoadingDetail ? 'animate-spin' : ''}`} />
                    Fetch from OpenAQ
                  </button>
                  <button
                    onClick={() => setSelectedStation(null)}
                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-400" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6">
                {isLoadingDetail ? (
                  <div className="flex flex-col justify-center items-center h-64 gap-4">
                    <Loader className="w-8 h-8 animate-spin text-blue-500" />
                    <div className="text-center">
                      <p className="text-gray-300 font-medium">Fetching Latest Data</p>
                      <p className="text-gray-400 text-sm mt-1">Connecting to OpenAQ...</p>
                    </div>
                  </div>
                ) : stationDetail ? (
                  <div className="space-y-6">
                    {/* Station Info */}
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-3">Station Information</h3>
                      <div className="bg-white/5 rounded-lg p-4 space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Data Source:</span>
                          <span className="text-white font-medium">{stationDetail.data_source}</span>
                        </div>
                        {stationDetail.openaq_location_id && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">OpenAQ Location ID:</span>
                            <span className="text-white font-mono text-xs">{stationDetail.openaq_location_id}</span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span className="text-gray-400">Status:</span>
                          <span className={`font-medium ${stationDetail.is_active ? 'text-green-400' : 'text-red-400'}`}>
                            {stationDetail.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                        {stationDetail.last_updated && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">Last Updated:</span>
                            <span className="text-green-400 font-medium text-xs">
                              {new Date(stationDetail.last_updated).toLocaleString()}
                            </span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span className="text-gray-400">Coordinates:</span>
                          <span className="text-white font-mono text-xs">
                            {stationDetail.location.lat.toFixed(4)}, {stationDetail.location.lng.toFixed(4)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Latest Readings - Table Format */}
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-3">Latest Readings</h3>
                      {Object.keys(stationDetail.latest_readings).length > 0 ? (
                        <div className="bg-slate-950 border border-white/10 rounded-lg overflow-hidden">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-white/10 bg-white/5">
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 uppercase">Parameter</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 uppercase">Value</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 uppercase">Normalized</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 uppercase">Unit</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 uppercase">Timestamp</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(stationDetail.latest_readings).map(([param, reading]) => (
                                <tr key={param} className="border-b border-white/5 hover:bg-white/5">
                                  <td className="px-4 py-3">
                                    <span className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded text-xs font-medium">
                                      {param.toUpperCase()}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-white font-semibold">
                                    {reading.value.toFixed(2)}
                                  </td>
                                  <td className="px-4 py-3 text-gray-300">
                                    {reading.value_normalized.toFixed(2)}
                                  </td>
                                  <td className="px-4 py-3 text-gray-400">
                                    {reading.unit}
                                  </td>
                                  <td className="px-4 py-3 text-gray-400 text-xs font-mono">
                                    {new Date(reading.timestamp).toLocaleString()}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-6 text-center">
                          <p className="text-orange-300 font-medium text-lg mb-2">
                            ⚠️ No Data Available from OpenAQ
                          </p>
                          <p className="text-orange-300/70 text-sm mb-3">
                            This station's sensors are not currently reporting measurements to OpenAQ.
                          </p>
                          <div className="text-xs text-orange-300/50 space-y-1">
                            <p>Possible reasons:</p>
                            <p>• Sensors may be inactive or offline</p>
                            <p>• Station may not have reported data in the last 7 days</p>
                            <p>• OpenAQ Location ID: {stationDetail.openaq_location_id || 'N/A'}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Latest Readings - JSON Format */}
                    <div>
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="text-lg font-semibold text-white">Latest Readings (JSON)</h3>
                        {Object.keys(stationDetail.latest_readings).length > 0 && (
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(JSON.stringify(stationDetail.latest_readings, null, 2));
                            }}
                            className="px-2 py-1 bg-green-500/20 hover:bg-green-500/30 border border-green-500/50 rounded text-xs text-green-300 transition-colors flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" />
                            Copy
                          </button>
                        )}
                      </div>
                      {Object.keys(stationDetail.latest_readings).length > 0 ? (
                        <div className="bg-slate-950 border border-white/10 rounded-lg p-4 overflow-x-auto">
                          <pre className="text-xs font-mono">
                            <code className="language-json">
                              {JSON.stringify(stationDetail.latest_readings, null, 2)
                                .split('\n')
                                .map((line, i) => {
                                  let colorClass = 'text-gray-300';
                                  if (line.includes('"timestamp"') || line.includes('"value"') || line.includes('"unit"')) {
                                    colorClass = 'text-blue-400';
                                  } else if (line.match(/:\s*"[^"]*"/)) {
                                    colorClass = 'text-green-400';
                                  } else if (line.match(/:\s*\d+/)) {
                                    colorClass = 'text-yellow-400';
                                  } else if (line.includes('{') || line.includes('}')) {
                                    colorClass = 'text-purple-400';
                                  }
                                  return (
                                    <div key={i} className={colorClass}>
                                      {line}
                                    </div>
                                  );
                                })}
                            </code>
                          </pre>
                        </div>
                      ) : (
                        <div className="bg-slate-950 border border-white/10 rounded-lg p-4">
                          <pre className="text-xs text-orange-400 font-mono">
                            {JSON.stringify({ message: "No recent data available for this station" }, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>

                    {/* Full Station Details - JSON */}
                    <div>
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="text-lg font-semibold text-white">Complete Station Data (JSON)</h3>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(JSON.stringify(stationDetail, null, 2));
                          }}
                          className="px-2 py-1 bg-green-500/20 hover:bg-green-500/30 border border-green-500/50 rounded text-xs text-green-300 transition-colors flex items-center gap-1"
                        >
                          <Copy className="w-3 h-3" />
                          Copy
                        </button>
                      </div>
                      <div className="bg-slate-950 border border-white/10 rounded-lg p-4 overflow-x-auto max-h-96 overflow-y-auto">
                        <pre className="text-xs font-mono">
                          <code className="language-json">
                            {JSON.stringify(stationDetail, null, 2)
                              .split('\n')
                              .map((line, i) => {
                                let colorClass = 'text-gray-300';
                                if (line.includes('"id"') || line.includes('"name"') || line.includes('"province"')) {
                                  colorClass = 'text-cyan-400';
                                } else if (line.match(/:\s*"[^"]*"/)) {
                                  colorClass = 'text-green-400';
                                } else if (line.match(/:\s*\d+(\.\d+)?(?!.*")/)) {
                                  colorClass = 'text-yellow-400';
                                } else if (line.match(/:\s*(true|false|null)/)) {
                                  colorClass = 'text-orange-400';
                                } else if (line.includes('{') || line.includes('}') || line.includes('[') || line.includes(']')) {
                                  colorClass = 'text-purple-400';
                                }
                                return (
                                  <div key={i} className={colorClass}>
                                    {line}
                                  </div>
                                );
                              })}
                          </code>
                        </pre>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-400">
                    Failed to load station details
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
