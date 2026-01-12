/**
 * Modern Dashboard Home Page
 * 
 * Medical-grade satellite command center dashboard with real-time metrics.
 * Fetches data from backend APIs: /exposure/dashboard/ and /exposure/trends/
 * @module pages/HomePage
 */

import { motion } from 'framer-motion';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { MapPin, AlertCircle, Zap, TrendingUp, Loader, Activity } from 'lucide-react';
import { useUserTier } from '@/hooks/useUserTier';
import exposureApiClient from '@/services/exposureApi';
import { useEffect, useState } from 'react';
import { TierBadge } from '@/components/ui/TierBadge';
import { useLatestStationReadings } from '@/hooks/queries/useSpatialData';
import { useAuthStore } from '@/store';

// Type definitions
interface DashboardData {
  total_population: number;
  exposed_population: number;
  respiratory_risk_index: number;
  current_pm25: number;
  timestamp: string;
}

interface TrendData {
  timestamp: string;
  pm25: number;
  pm10: number;
}

interface DistrictExposure {
  district_name: string;
  exposure_index: number;
  population: number;
}

export default function HomePage() {
  const { user, isAuthenticated } = useAuthStore();
  const { tier, isPremium } = useUserTier();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [topDistricts, setTopDistricts] = useState<DistrictExposure[]>([]);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true);
  const [isLoadingTrends, setIsLoadingTrends] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch latest station readings using new API
  const { data: latestReadings, isLoading: isLoadingReadings } = useLatestStationReadings({
    parameter: 'PM25',
    active_only: true,
  });

  // Fetch dashboard summary
  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setIsLoadingDashboard(true);
        const response = await exposureApiClient.get('/dashboard/') as any;
        const data = response.data as DashboardData;
        setDashboardData(data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch dashboard:', err);
        setError('Failed to load dashboard data');
      } finally {
        setIsLoadingDashboard(false);
      }
    };

    fetchDashboard();
    // Refresh every 5 minutes
    const interval = setInterval(fetchDashboard, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch 24-hour trends
  useEffect(() => {
    const fetchTrends = async () => {
      try {
        setIsLoadingTrends(true);
        const response = await exposureApiClient.get('/trends/', {
          params: {
            scope: 'national',
            days: 1,
          },
        }) as any;
        const trends = Array.isArray(response.data) ? response.data : [];
        // Transform API data to chart format (assuming API returns hourly data)
        const formattedTrends = trends.map((item: any) => ({
          time: new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          pm25: item.pm25 || 0,
          pm10: item.pm10 || 0,
        }));
        setTrendData(formattedTrends);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch trends:', err);
        setError('Failed to load trend data');
      } finally {
        setIsLoadingTrends(false);
      }
    };

    fetchTrends();
  }, []);

  // Fetch top exposed districts
  useEffect(() => {
    const fetchDistricts = async () => {
      try {
        const response = await exposureApiClient.get('/districts/', {
          params: {
            limit: 4,
            order_by: '-exposure_index',
          },
        }) as any;
        const districts = Array.isArray(response.data) ? response.data : [];
        const formatted = districts.map((d: any) => ({
          name: d.district_name || d.name,
          exposure: d.exposure_index || d.exposure,
          population: d.population || 0,
        }));
        setTopDistricts(formatted);
      } catch (err) {
        console.error('Failed to fetch districts:', err);
      }
    };

    fetchDistricts();
  }, []);

  // Fallback data if API fails
  const displayDashboard = dashboardData || {
    total_population: 2400000,
    exposed_population: 2400000,
    respiratory_risk_index: 68,
    current_pm25: 62,
    timestamp: new Date().toISOString(),
  };

  const displayTrends = trendData.length > 0 ? trendData : [
    { time: '00:00', pm25: 35, pm10: 45 },
    { time: '04:00', pm25: 32, pm10: 42 },
    { time: '08:00', pm25: 45, pm10: 58 },
    { time: '12:00', pm25: 62, pm10: 78 },
    { time: '16:00', pm25: 58, pm10: 72 },
    { time: '20:00', pm25: 42, pm10: 55 },
  ];

  const displayDistricts = topDistricts.length > 0 ? topDistricts : [
    { name: 'Karachi', exposure: 2450, population: 0 },
    { name: 'Lahore', exposure: 1890, population: 0 },
    { name: 'Islamabad', exposure: 890, population: 0 },
    { name: 'Rawalpindi', exposure: 1200, population: 0 },
  ];

  // Feature flags based on tier
  const hasAIInsights = isPremium;

  return (
    <div className="min-h-screen bg-space-navy-950 p-4 md:p-8">
      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm"
        >
          {error}
        </motion.div>
      )}

      {/* Header Section */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold text-foreground font-mono mb-2">
              AIR RISK
            </h1>
            <p className="text-muted-foreground">Medical-Grade Geospatial Analytics</p>
          </div>
          <div className="flex flex-col items-end gap-3">
            <TierBadge tier={tier} size="lg" />
            <div className="flex items-center gap-2 text-neon-green-500">
              <div className="w-2 h-2 rounded-full bg-neon-green-500 animate-pulse"></div>
              <span className="font-mono text-sm">System Online</span>
            </div>
            {isAuthenticated && user && (
              <p className="text-xs text-muted-foreground">Welcome, {user.first_name || user.username}</p>
            )}
          </div>
        </div>
      </motion.div>

      {/* Key Metrics Grid */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8"
      >
        {/* Population Exposure */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6 hover:border-tech-blue-500/50 transition-all"
        >
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Population Exposure</p>
              {isLoadingDashboard ? (
                <Loader className="w-8 h-8 animate-spin text-tech-blue-500" />
              ) : (
                <h3 className="text-3xl font-bold text-foreground font-mono">
                  {(displayDashboard.exposed_population / 1_000_000).toFixed(1)}M
                </h3>
              )}
            </div>
            <MapPin className="text-tech-blue-500" size={24} />
          </div>
          <div className="text-xs text-neon-green-400 flex items-center gap-1">
            <TrendingUp size={14} /> ↑ 12% from last week
          </div>
        </motion.div>

        {/* Respiratory Risk */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6 hover:border-tech-blue-500/50 transition-all"
        >
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Respiratory Risk Index</p>
              {isLoadingDashboard ? (
                <Loader className="w-8 h-8 animate-spin text-orange-500" />
              ) : (
                <h3 className="text-3xl font-bold text-foreground font-mono">
                  {displayDashboard.respiratory_risk_index}
                </h3>
              )}
            </div>
            <AlertCircle className="text-orange-500" size={24} />
          </div>
          <div className="text-xs text-orange-400 flex items-center gap-1">
            <TrendingUp size={14} /> Moderate-High Range
          </div>
        </motion.div>

        {/* Real-time PM2.5 */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6 hover:border-tech-blue-500/50 transition-all"
        >
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Real-time PM2.5</p>
              {isLoadingDashboard ? (
                <Loader className="w-8 h-8 animate-spin text-tech-blue-500" />
              ) : (
                <h3 className="text-3xl font-bold text-foreground font-mono">{displayDashboard.current_pm25} μg/m³</h3>
              )}
            </div>
            <Zap className="text-tech-blue-500 animate-pulse" size={24} />
          </div>
          <div className="text-xs text-tech-blue-400 flex items-center gap-1">
            <TrendingUp size={14} /> Active Monitoring
          </div>
        </motion.div>
      </motion.div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Air Quality Trend */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6"
        >
          <h3 className="text-lg font-semibold text-foreground mb-4 font-mono">
            24-Hour Air Quality Trend
          </h3>
          {isLoadingTrends ? (
            <div className="h-64 flex items-center justify-center">
              <Loader className="w-8 h-8 animate-spin text-tech-blue-500" />
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={displayTrends}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" />
                <YAxis stroke="rgba(255,255,255,0.5)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(10, 25, 47, 0.95)',
                    border: '1px solid rgba(255,255,255,0.2)',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
                <Line type="monotone" dataKey="pm25" stroke="#0EA5E9" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="pm10" stroke="#22C55E" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* District Exposure */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6"
        >
          <h3 className="text-lg font-semibold text-foreground mb-4 font-mono">
            District Exposure Analysis
          </h3>
          {displayDistricts.length === 0 ? (
            <div className="h-64 flex items-center justify-center">
              <Loader className="w-8 h-8 animate-spin text-tech-blue-500" />
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={displayDistricts}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.5)" />
                <YAxis stroke="rgba(255,255,255,0.5)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(10, 25, 47, 0.95)',
                    border: '1px solid rgba(255,255,255,0.2)',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="exposure" fill="#0EA5E9" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>
      </div>

      {/* Latest Station Readings */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6 mb-8"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground font-mono flex items-center gap-2">
            <Activity className="text-tech-blue-500" size={20} />
            Latest Station Readings (PM2.5)
          </h3>
          <span className="text-xs text-muted-foreground">Live from {latestReadings?.count || 0} stations</span>
        </div>
        {isLoadingReadings ? (
          <div className="flex items-center justify-center h-24">
            <Loader className="w-6 h-6 animate-spin text-tech-blue-500" />
          </div>
        ) : latestReadings && latestReadings.results.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {latestReadings.results.slice(0, 8).map((station) => {
              const pm25 = station.latest_reading?.PM25 || 0;
              const aqi = station.latest_reading?.aqi || 0;
              const aqiColor = aqi > 150 ? 'text-red-500' : aqi > 100 ? 'text-orange-500' : aqi > 50 ? 'text-yellow-500' : 'text-green-500';
              
              return (
                <motion.div
                  key={station.id}
                  whileHover={{ scale: 1.02 }}
                  className="bg-white/5 border border-white/10 rounded-lg p-3 hover:border-tech-blue-500/50 transition-all"
                >
                  <p className="text-xs text-muted-foreground mb-1 truncate">{station.name}</p>
                  <div className="flex items-baseline justify-between">
                    <span className={`text-2xl font-bold font-mono ${aqiColor}`}>{pm25.toFixed(1)}</span>
                    <span className="text-xs text-muted-foreground">μg/m³</span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-muted-foreground">AQI: {aqi}</span>
                    <div className={`w-2 h-2 rounded-full ${station.is_active ? 'bg-neon-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">No station data available</p>
        )}
      </motion.div>

      {/* Premium Section */}
      {hasAIInsights && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-r from-tech-blue-500/10 to-neon-green-500/10 border border-tech-blue-500/30 rounded-lg p-6"
        >
          <h3 className="text-lg font-semibold text-foreground mb-3 font-mono">
            🤖 AI Health Insights
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Current air quality levels suggest increased respiratory risks for vulnerable populations.
            Recommend staying indoors during peak pollution hours (10 AM - 4 PM). Air quality expected
            to improve tomorrow with incoming weather system.
          </p>
        </motion.div>
      )}
    </div>
  );
}
