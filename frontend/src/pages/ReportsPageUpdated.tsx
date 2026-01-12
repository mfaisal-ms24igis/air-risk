/**
 * Updated Reports Page
 * 
 * Generate premium PDF reports with:
 * - GIS analyst narrative (AI-powered)
 * - Professional maps with satellite overlays
 * - Comprehensive visualizations (PM2.5 trends, pollutant comparison, AQI gauge)
 * - Uses latest backend /reports/generate/ endpoint
 * 
 * @module pages/ReportsPageUpdated
 */

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Loader, AlertCircle, Check, Calendar, MapPin, Sparkles, Target } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useUserTier } from '@/hooks/useUserTier';
import { TierBadge, UpgradePrompt } from '@/components/ui/TierBadge';
import { useDistricts } from '@/hooks/queries/useSpatialData';
import { apiClient } from '@/core/api/client';
import { useToast } from '@/contexts/ToastContext';
import { CardSkeleton } from '@/components/ui/Skeleton';
import { MapBase } from '@/components/map';
import { Map as MapLibreMap, Marker } from 'maplibre-gl';

export default function ReportsPageUpdated() {
  const { user } = useAuth();
  const { tier, isPremium } = useUserTier();
  const { success, error: showError } = useToast();
  
  // Fetch districts using new API
  const { data: districtsData, isLoading: loadingDistricts } = useDistricts();
  
  // Form state
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [latitude, setLatitude] = useState(31.5204);
  const [longitude, setLongitude] = useState(74.3587);
  const [radius, setRadius] = useState(5);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const [marker, setMarker] = useState<Marker | null>(null);
  const [generatedReport, setGeneratedReport] = useState<{
    id: number;
    pdf_url: string;
    filename: string;
  } | null>(null);

  // Set date defaults
  useState(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
  });

  // Handle map click to select location
  const handleMapClick = useCallback((e: any) => {
    const { lng, lat } = e.lngLat;
    setLongitude(lng);
    setLatitude(lat);

    // Remove old marker if exists
    setMarker(prev => {
      if (prev) {
        prev.remove();
      }
      // Add new marker
      if (map) {
        const newMarker = new Marker({ color: '#3b82f6', scale: 1.2 })
          .setLngLat([lng, lat])
          .addTo(map);
        return newMarker;
      }
      return null;
    });
  }, [map]);

  // Initialize map with default location marker
  const handleMapLoad = useCallback((loadedMap: MapLibreMap) => {
    console.log('Map loaded');
    setMap(loadedMap);

    // Add initial marker immediately (map is already loaded when this callback fires)
    const initialMarker = new Marker({ color: '#3b82f6', scale: 1.2, draggable: false })
      .setLngLat([longitude, latitude])
      .addTo(loadedMap);
    setMarker(initialMarker);
    
    // Add click handler for location selection
    const handleMapClick = (e: any) => {
      const { lng, lat } = e.lngLat;
      console.log('Map clicked:', lng, lat);
      setLongitude(lng);
      setLatitude(lat);
      
      // Update marker position
      initialMarker.setLngLat([lng, lat]);
    };
    
    loadedMap.on('click', handleMapClick);
    console.log('✅ Click handler attached to map');
    
    // Make sure map is interactive
    loadedMap.dragPan.enable();
    loadedMap.scrollZoom.enable();
    loadedMap.touchZoomRotate.enable();
    
    // Change cursor on hover to indicate map is clickable
    loadedMap.getCanvas().style.cursor = 'crosshair';
  }, [longitude, latitude]);

  const pollReportStatus = async (reportId: number, maxAttempts = 30) => {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, 3000)); // Wait 3 seconds
      
      try {
        // NOTE: apiClient.get() returns response.data directly
        const statusData = await apiClient.get(`/reports/${reportId}/status/`);
        
        console.log(`Poll ${i+1}/${maxAttempts}:`, statusData);
        
        // Handle nested data structure if present
        const status = statusData?.data?.status || statusData?.status;
        
        if (!status) {
          console.warn('No status in response:', statusData);
          continue; // Continue polling
        }
        
        if (status === 'COMPLETED' || status === 'completed') {
          // Return the status data directly (it contains all report info)
          console.log('✅ Report completed:', statusData);
          return statusData?.data || statusData;
        } else if (status === 'FAILED' || status === 'failed') {
          const error = statusData?.data?.error || statusData?.error || 'Report generation failed';
          throw new Error(error);
        }
        // Continue polling if still pending/generating
      } catch (err: any) {
        // Don't retry on 404 or other errors
        if (err.response?.status === 404) {
          console.error('Report not found, stopping poll');
          throw new Error('Report not found');
        }
        console.error('Error polling status:', err.message);
        // Continue polling on network errors
      }
    }
    throw new Error('Report generation timeout (90 seconds)');
  };

  const handleGenerateReport = async () => {
    if (!isPremium) {
      showError('Premium subscription required to generate reports');
      return;
    }

    if (!latitude || !longitude || !startDate || !endDate) {
      showError('Please fill all required fields');
      return;
    }

    try {
      setIsGenerating(true);
      setGeneratedReport(null);

      console.log('🚀 Sending report request:', {
        lat: latitude,
        lng: longitude,
        radius_km: radius,
        start_date: startDate,
        end_date: endDate,
      });

      // Call new backend endpoint
      // NOTE: apiClient.post() returns response.data directly, not the full response object
      let responseData;
      try {
        responseData = await apiClient.post('/reports/generate/', {
          lat: latitude,
          lng: longitude,
          radius_km: radius,
          start_date: startDate,
          end_date: endDate,
        });
      } catch (apiError: any) {
        console.error('❌ API call failed:', apiError);
        console.error('Error details:', {
          message: apiError.message,
          response: apiError.response,
          status: apiError.response?.status,
          data: apiError.response?.data,
        });
        throw new Error(apiError.response?.data?.error || apiError.message || 'API request failed');
      }

      console.log('✅ API response data:', responseData);
      
      // Check if response is valid
      if (!responseData) {
        throw new Error('Invalid API response - no data returned');
      }
      
      // Handle different response structures
      let reportId;
      let taskData = responseData;
      
      // Try different nested structures
      if (taskData.data) taskData = taskData.data;
      if (taskData.report_id) {
        reportId = taskData.report_id;
      } else if (taskData.id) {
        reportId = taskData.id;
      } else {
        console.error('Response structure:', JSON.stringify(taskData, null, 2));
        throw new Error('No report ID in response');
      }
      
      success('Report generation started. Please wait...');
      
      // Poll for completion
      const completedReport = await pollReportStatus(reportId);
      
      console.log('📊 Completed report data:', completedReport);
      console.log('Available keys:', Object.keys(completedReport));
      
      // Extract download URL from response or construct it manually
      const finalReportId = completedReport?.report_id || completedReport?.id || reportId;
      let downloadUrl = completedReport?.download_url || completedReport?.data?.download_url;
      
      // If no download_url provided, construct it manually
      // (Backend may not include it due to case-sensitive status check)
      if (!downloadUrl) {
        console.warn('⚠️ No download_url in response, constructing manually');
        // Note: Router adds 'reports/' prefix, so full path is /api/v1/reports/reports/{id}/download/
        downloadUrl = `/api/v1/reports/reports/${finalReportId}/download/`;
      }
      
      // Build full URL (download_url is relative like '/api/v1/reports/reports/123/download/')
      const fullPdfUrl = `http://localhost:8000${downloadUrl}`;
      
      console.log('✅ PDF download URL:', fullPdfUrl);
      
      setGeneratedReport({
        id: finalReportId,
        pdf_url: fullPdfUrl,
        filename: `air-quality-report-${finalReportId}.pdf`,
      });
      
      success('Report generated successfully!');
    } catch (err: any) {
      let message = err.response?.data?.error || err.message || 'Failed to generate report';
      
      // Handle rate limiting specifically
      if (err.response?.status === 429) {
        message = 'Rate limit exceeded. Please wait 1-2 minutes before generating another report.';
      }
      
      showError(message);
      console.error('Report generation error:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (!generatedReport?.pdf_url) return;

    try {
      console.log('🔽 Downloading from:', generatedReport.pdf_url);
      
      // Fetch with auth token
      const token = localStorage.getItem('token') || localStorage.getItem('access_token');
      const response = await fetch(generatedReport.pdf_url, {
        method: 'GET',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }

      // Get blob and create download link
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = generatedReport.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      success('Report downloaded successfully!');
    } catch (err: any) {
      console.error('Download error:', err);
      showError('Failed to download report: ' + err.message);
    }
  };

  return (
    <div className="min-h-screen bg-space-navy-950 p-4 md:p-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-4xl font-bold text-foreground font-mono mb-2">
              Premium Reports
            </h1>
            <p className="text-muted-foreground">
              Generate professional PDF reports with AI insights, maps, and visualizations
            </p>
          </div>
          <TierBadge tier={tier} size="lg" />
        </div>
      </motion.div>

      {!isPremium ? (
        <UpgradePrompt
          feature="PDF Report Generation with AI Insights"
          onUpgrade={() => window.location.href = '/upgrade'}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Report Configuration Form */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-2 bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6"
          >
            <h2 className="text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
              <FileText className="text-tech-blue-500" size={20} />
              Report Configuration
            </h2>

            <div className="space-y-6">
              {/* Interactive Map for Location Selection */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-3 flex items-center gap-2">
                  <Target size={16} className="text-tech-blue-500" />
                  Select Location on Map (Click to set point)
                </label>
                <div className="relative h-80 rounded-lg overflow-hidden border-2 border-tech-blue-500/40 shadow-lg shadow-tech-blue-500/20">
                  <MapBase
                    center={[longitude, latitude]}
                    zoom={10}
                    onLoad={handleMapLoad}
                    className="h-full"
                  />
                  <div className="absolute top-4 left-4 bg-black/80 backdrop-blur-sm px-4 py-2 rounded-lg border border-tech-blue-500/30 z-10">
                    <p className="text-xs text-muted-foreground">Selected Location:</p>
                    <p className="text-sm text-foreground font-mono">
                      {latitude.toFixed(4)}°N, {longitude.toFixed(4)}°E
                    </p>
                  </div>
                  <div className="absolute top-4 right-4 bg-tech-blue-500/90 backdrop-blur-sm px-3 py-2 rounded-lg border border-tech-blue-400 z-10 animate-pulse">
                    <p className="text-xs text-white font-semibold flex items-center gap-1">
                      <Target size={14} />
                      Click to Select Point
                    </p>
                  </div>
                </div>
                <p className="text-xs text-tech-blue-400 mt-2 font-medium">
                  👆 Click anywhere on the map to select your report center point. The blue marker will move to your selected location.
                </p>
              </div>

              {/* Radius Selector */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Analysis Radius
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="1"
                    max="50"
                    value={radius}
                    onChange={(e) => setRadius(parseInt(e.target.value))}
                    className="flex-1 accent-tech-blue-500"
                  />
                  <div className="flex items-center gap-2 min-w-[80px]">
                    <span className="text-2xl font-bold text-tech-blue-500">{radius}</span>
                    <span className="text-sm text-muted-foreground">km</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Analysis area: ~{Math.round(Math.PI * radius * radius)} km² | Stations within this radius will be included
                </p>
              </div>

              {/* Date Range */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  <Calendar size={16} className="inline mr-1" />
                  Date Range (30 days max)
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-tech-blue-500 transition-colors"
                    />
                    <p className="text-xs text-muted-foreground mt-1">Start Date</p>
                  </div>
                  <div>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-tech-blue-500 transition-colors"
                    />
                    <p className="text-xs text-muted-foreground mt-1">End Date</p>
                  </div>
                </div>
              </div>

              {/* Generate Button */}
              <button
                onClick={handleGenerateReport}
                disabled={isGenerating}
                className="w-full px-6 py-3 bg-gradient-to-r from-tech-blue-500 to-neon-green-500 text-white font-semibold rounded-lg hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    Generating Report...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Generate AI-Powered Report
                  </>
                )}
              </button>
            </div>
          </motion.div>

          {/* Report Preview / Download */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6"
          >
            <h2 className="text-xl font-semibold text-foreground mb-6">Report Preview</h2>

            {isGenerating ? (
              <div className="flex flex-col items-center justify-center h-64">
                <Loader className="w-12 h-12 animate-spin text-tech-blue-500 mb-4" />
                <p className="text-sm text-muted-foreground text-center">
                  Generating your report...<br />
                  This may take 30-60 seconds
                </p>
              </div>
            ) : generatedReport ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-neon-green-500 mb-4">
                  <Check className="w-5 h-5" />
                  <span className="text-sm font-medium">Report Ready</span>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                  <p className="text-sm text-foreground mb-2">
                    <strong>Report ID:</strong> {generatedReport.id}
                  </p>
                  <p className="text-sm text-foreground mb-2">
                    <strong>Filename:</strong> {generatedReport.filename}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Report includes:
                  </p>
                  <ul className="text-xs text-muted-foreground list-disc list-inside mt-2 space-y-1">
                    <li>AI-generated GIS analyst narrative</li>
                    <li>Professional location map with satellite overlay</li>
                    <li>PM2.5 trend analysis chart</li>
                    <li>Pollutant comparison (ground vs satellite)</li>
                    <li>AQI gauge visualization</li>
                    <li>Health risk assessment</li>
                  </ul>
                </div>

                <button
                  onClick={handleDownload}
                  className="w-full px-4 py-3 bg-tech-blue-500 text-white font-medium rounded-lg hover:bg-tech-blue-600 transition-colors flex items-center justify-center gap-2"
                >
                  <Download className="w-5 h-5" />
                  Download PDF Report
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <FileText className="w-16 h-16 text-muted-foreground mb-4" />
                <p className="text-sm text-muted-foreground">
                  Configure your report settings and click Generate to create a professional PDF report
                </p>
              </div>
            )}
          </motion.div>
        </div>
      )}

      {/* Features List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-8 bg-gradient-to-r from-tech-blue-500/10 to-neon-green-500/10 border border-tech-blue-500/30 rounded-lg p-6"
      >
        <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
          <Sparkles className="text-tech-blue-500" />
          Report Features
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { title: 'AI-Powered Analysis', desc: 'GIS analyst persona generates professional narrative' },
            { title: 'Satellite Integration', desc: 'Google Earth Engine Sentinel-5P data overlay' },
            { title: 'Comprehensive Charts', desc: '5 visualization types with WHO guidelines' },
            { title: 'Location Maps', desc: 'Enhanced maps with gradient backgrounds' },
            { title: 'Trend Analysis', desc: '30-day PM2.5 trends with health thresholds' },
            { title: 'Health Assessment', desc: 'AQI-based risk categorization' },
          ].map((feature, idx) => (
            <div key={idx} className="bg-white/5 border border-white/10 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-foreground mb-1">{feature.title}</h4>
              <p className="text-xs text-muted-foreground">{feature.desc}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
