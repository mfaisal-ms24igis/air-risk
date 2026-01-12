import { useState, useEffect } from 'react';
import { SatelliteCommandLayout } from '@/components/layout/SatelliteCommandLayout';
import { PakistanBaseMap } from '@/features/map/PakistanBaseMap';
import { DrilldownMap } from '@/features/map/components/DrilldownMap';
import {
  DataPanel,
  StatsGrid,
  PopulationExposureCard,
  RespiratoryRiskCard,
  RealtimePM25Card,
  AlertCard,
} from '@/components/dashboard/DataPanels';
import { ReportGenerator } from '@/features/reports/ReportGenerator';
import { useUserTier } from '@/hooks/useUserTier';
import { MapPin, Layers, Clock, TrendingUp } from 'lucide-react';
import { LngLatBoundsLike } from 'maplibre-gl';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

interface DrilldownState {
  districtId: string;
  districtName: string;
  bounds: LngLatBoundsLike;
}

export function DashboardPage() {
  const { isPremium } = useUserTier();
  const [drilldown, setDrilldown] = useState<DrilldownState | null>(null);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | undefined>();
  const [liveData, setLiveData] = useState({
    populationExposure: 2847392,
    respiratoryRisk: 6.8,
    pm25: 68.4,
    alerts: 12,
  });

  // Get user location (PREMIUM feature)
  useEffect(() => {
    if (isPremium && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        (error) => {
          console.warn('Geolocation error:', error);
        }
      );
    }
  }, [isPremium]);

  // Fetch live data updates
  useEffect(() => {
    const fetchLiveData = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        const response = await axios.get(
          'http://127.0.0.1:8000/api/v1/exposure/district-exposure/',
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (response.data.results?.length > 0) {
          const totals = response.data.results.reduce(
            (acc: any, district: any) => ({
              population: acc.population + (district.exposed_population || 0),
              risk: Math.max(acc.risk, district.health_risk_score || 0),
            }),
            { population: 0, risk: 0 }
          );

          setLiveData((prev) => ({
            ...prev,
            populationExposure: totals.population,
            respiratoryRisk: totals.risk,
          }));
        }
      } catch (error) {
        console.error('Failed to fetch live data:', error);
      }
    };

    fetchLiveData();
    const interval = setInterval(fetchLiveData, 30000); // Update every 30s

    return () => clearInterval(interval);
  }, []);

  const handleDistrictClick = (
    districtId: string,
    districtName: string,
    bounds: LngLatBoundsLike
  ) => {
    if (isPremium) {
      setDrilldown({ districtId, districtName, bounds });
    }
  };

  const handleCloseDrilldown = () => {
    setDrilldown(null);
  };

  return (
    <SatelliteCommandLayout
      rightPanel={
        <>
          {/* Live Metrics */}
          <DataPanel
            title="Live Metrics"
            subtitle="Real-time environmental data"
            icon={<TrendingUp className="h-5 w-5" />}
          >
            <StatsGrid>
              <PopulationExposureCard
                value={liveData.populationExposure}
                trend={8.2}
              />
              <RespiratoryRiskCard
                value={liveData.respiratoryRisk}
                trend={-2.1}
              />
              <RealtimePM25Card value={liveData.pm25} trend={12.5} />
              <AlertCard count={liveData.alerts} severity="high" />
            </StatsGrid>
          </DataPanel>

          {/* Time Controls */}
          <DataPanel
            title="Temporal Analysis"
            subtitle="Historical data exploration"
            icon={<Clock className="h-5 w-5" />}
          >
            <div className="space-y-3">
              <div className="glass-panel p-3">
                <label className="block text-xs font-mono text-gray-400 mb-2">
                  TIME RANGE
                </label>
                <input
                  type="range"
                  min="0"
                  max="30"
                  defaultValue="0"
                  className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer slider"
                  title="Select time range"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>30 days ago</span>
                  <span>Today</span>
                </div>
              </div>

              <div className="glass-panel p-3">
                <label className="block text-xs font-mono text-gray-400 mb-2">
                  QUICK SELECT
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {['24h', '7d', '14d', '30d'].map((period) => (
                    <button
                      key={period}
                      className="px-3 py-2 text-xs font-mono bg-white/5 hover:bg-tech-blue-500/20 border border-white/10 hover:border-tech-blue-500/50 rounded transition-all"
                    >
                      {period}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </DataPanel>

          {/* Layer Controls */}
          <DataPanel
            title="Data Layers"
            subtitle="Satellite & ground data"
            icon={<Layers className="h-5 w-5" />}
          >
            <div className="space-y-2">
              {[
                { name: 'NO₂ (Sentinel-5P)', active: true },
                { name: 'PM2.5 (Ground)', active: true },
                { name: 'SO₂ (Sentinel-5P)', active: false },
                { name: 'CO (Sentinel-5P)', active: false },
                { name: 'O₃ (Sentinel-5P)', active: false },
                { name: 'Population Density', active: true },
              ].map((layer) => (
                <div
                  key={layer.name}
                  className="flex items-center justify-between p-3 glass-panel hover:bg-white/10 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`h-2 w-2 rounded-full ${layer.active ? 'bg-neon-green-500 animate-pulse' : 'bg-gray-600'
                        }`}
                    />
                    <span className="text-sm text-gray-300">{layer.name}</span>
                  </div>
                  <input
                    type="checkbox"
                    defaultChecked={layer.active}
                    className="toggle"
                    title={`Toggle ${layer.name}`}
                  />
                </div>
              ))}
            </div>
          </DataPanel>

          {/* Report Generator (PREMIUM) */}
          {isPremium && (
            <ReportGenerator
              userLocation={userLocation}
              districtId={drilldown?.districtId}
              districtName={drilldown?.districtName}
            />
          )}
        </>
      }
    >
      {/* Map View */}
      <div className="relative h-full w-full">
        <AnimatePresence mode="wait">
          {drilldown ? (
            <motion.div
              key="drilldown"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="h-full"
            >
              <DrilldownMap
                districtId={drilldown.districtId}
                districtName={drilldown.districtName}
                bounds={drilldown.bounds}
                userLocation={userLocation}
                onClose={handleCloseDrilldown}
              />
            </motion.div>
          ) : (
            <motion.div
              key="main"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="h-full"
            >
              <PakistanBaseMap
                onDistrictClick={handleDistrictClick}
                enableInteraction={isPremium}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Map Overlay: Title & Subtitle */}
        <div className="absolute top-6 left-6 z-10 max-w-md">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel-heavy p-6"
          >
            <h2 className="text-2xl font-bold text-white mb-1">
              {drilldown ? drilldown.districtName : 'Pakistan'}
            </h2>
            <p className="text-sm text-gray-400 font-mono">
              {drilldown
                ? 'District-level analysis • Premium View'
                : 'National air quality monitoring'}
            </p>
            {drilldown && (
              <div className="mt-3 pt-3 border-t border-white/10">
                <div className="flex items-center gap-2 text-xs text-tech-blue-400">
                  <MapPin className="h-4 w-4" />
                  <span>Sentinel-5P Multi-pollutant Analysis</span>
                </div>
              </div>
            )}
          </motion.div>
        </div>

        {/* Map Legend */}
        <div className="absolute bottom-6 left-6 z-10">
          <div className="glass-panel p-4 min-w-[200px]">
            <h4 className="text-xs font-mono text-gray-400 mb-3">AQI SCALE</h4>
            <div className="space-y-2">
              {[
                { label: 'Good', color: 'bg-neon-green-500', range: '0-50' },
                { label: 'Moderate', color: 'bg-yellow-500', range: '51-100' },
                { label: 'USG', color: 'bg-orange-500', range: '101-150' },
                { label: 'Unhealthy', color: 'bg-red-500', range: '151-200' },
                { label: 'V. Unhealthy', color: 'bg-purple-500', range: '201-300' },
                { label: 'Hazardous', color: 'bg-red-700', range: '300+' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className={`h-3 w-3 rounded ${item.color}`} />
                    <span className="text-gray-300">{item.label}</span>
                  </div>
                  <span className="text-gray-500 font-mono">{item.range}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Geolocation Button (PREMIUM) */}
        {isPremium && !drilldown && (
          <motion.button
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
            onClick={() => {
              if ('geolocation' in navigator) {
                navigator.geolocation.getCurrentPosition((position) => {
                  setUserLocation({
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                  });
                });
              }
            }}
            className="absolute bottom-6 right-6 z-10 p-4 glass-panel-heavy hover:bg-white/15 transition-all group"
          >
            <MapPin className="h-6 w-6 text-tech-blue-400 group-hover:text-tech-blue-300" />
          </motion.button>
        )}
      </div>
    </SatelliteCommandLayout>
  );
}
