/**
 * Modern Reports Page
 * 
 * Generate and manage air quality reports with backend integration.
 * Fetches districts from /air-quality/districts/
 * Posts reports to /exposure/reports/location/
 * @module pages/ReportsPage
 */

import { motion } from 'framer-motion';
import { DownloadCloud, FileText, Zap, Loader } from 'lucide-react';
import { useUserTier } from '@/hooks/useUserTier';
import { useEffect, useState } from 'react';
import apiClient from '@/services/api';
import exposureApiClient from '@/services/exposureApi';

interface District {
  id: number;
  name: string;
  district_name?: string;
}

interface Report {
  id: number;
  title: string;
  district_name: string;
  created_at: string;
  status: string;
}

export default function ReportsPage() {
  const { isPremium } = useUserTier();
  
  const [districts, setDistricts] = useState<District[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [isLoadingDistricts, setIsLoadingDistricts] = useState(true);
  const [isLoadingReports, setIsLoadingReports] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [reportType, setReportType] = useState('Exposure');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [pollutant, setPollutant] = useState('PM25');

  // Fetch districts
  useEffect(() => {
    const fetchDistricts = async () => {
      try {
        setIsLoadingDistricts(true);
        const response = await apiClient.get('/districts/');
        const districtList = Array.isArray(response.data) ? response.data : [];
        setDistricts(districtList);
        
        if (districtList.length > 0) {
          setSelectedDistrict(districtList[0].id?.toString() || '');
        }
        setError(null);
      } catch (err) {
        console.error('Failed to fetch districts:', err);
        setError('Failed to load districts');
        // Set sample districts
        const sampleDistricts = [
          { id: 1, name: 'Karachi', district_name: 'Karachi' },
          { id: 2, name: 'Lahore', district_name: 'Lahore' },
          { id: 3, name: 'Islamabad', district_name: 'Islamabad' },
          { id: 4, name: 'Rawalpindi', district_name: 'Rawalpindi' },
        ];
        setDistricts(sampleDistricts);
        setSelectedDistrict('1');
      } finally {
        setIsLoadingDistricts(false);
      }
    };

    fetchDistricts();
  }, []);

  // Fetch user reports (Premium only)
  useEffect(() => {
    if (!isPremium) {
      setIsLoadingReports(false);
      return;
    }

    const fetchReports = async () => {
      try {
        setIsLoadingReports(true);
        const response = await exposureApiClient.get('/reports/');
        const reportList = Array.isArray(response.data) ? response.data : [];
        setReports(reportList);
      } catch (err) {
        console.error('Failed to fetch reports:', err);
        // Sample reports for demo
        setReports([
          {
            id: 1,
            title: 'Karachi Exposure Report',
            district_name: 'Karachi',
            created_at: new Date(Date.now() - 86400000).toISOString(),
            status: 'completed',
          },
        ]);
      } finally {
        setIsLoadingReports(false);
      }
    };

    fetchReports();
  }, [isPremium]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isPremium) {
      setError('Premium tier required to generate reports');
      return;
    }

    if (!selectedDistrict || !startDate || !endDate) {
      setError('Please fill all required fields');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setSuccess(null);

      // Create report
      const response = await exposureApiClient.post('/reports/location/', {
        district_id: parseInt(selectedDistrict),
        report_type: reportType.toLowerCase(),
        pollutant: pollutant,
        start_date: startDate,
        end_date: endDate,
      });

      setSuccess(`Report queued for generation. ID: ${response.data?.id || 'pending'}`);

      // Reset form
      setReportType('Exposure');
      setStartDate('');
      setEndDate('');

      // Refresh reports list
      const reportsResponse = await exposureApiClient.get('/reports/');
      const reportList = Array.isArray(reportsResponse.data) ? reportsResponse.data : [];
      setReports(reportList);
    } catch (err) {
      console.error('Failed to create report:', err);
      setError('Failed to create report. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle report download
  const handleDownload = async (reportId: number) => {
    try {
      const response = await exposureApiClient.get(`/reports/${reportId}/download/`, {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data as Blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${reportId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentChild.removeChild(link);
    } catch (err) {
      console.error('Failed to download report:', err);
      setError('Failed to download report');
    }
  };

  return (
    <div className="min-h-screen bg-space-navy-950 p-4 md:p-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-4xl font-bold text-foreground font-mono mb-2">Generate Reports</h1>
        <p className="text-muted-foreground">
          {isPremium ? 'Create exposure and risk assessment reports' : 'Upgrade to Premium to generate reports'}
        </p>
      </motion.div>

      {/* Error/Success Messages */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm"
        >
          {error}
        </motion.div>
      )}
      {success && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-4 bg-neon-green-500/20 border border-neon-green-500/50 rounded-lg text-neon-green-300 text-sm"
        >
          {success}
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Report Generator */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-2"
        >
          <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-foreground font-mono mb-6">New Report</h3>

            {!isPremium ? (
              <div className="p-6 bg-neon-green-500/10 border border-neon-green-500/30 rounded-lg text-center">
                <p className="text-neon-green-300 mb-4">
                  ⭐ Report generation is a Premium feature
                </p>
                <p className="text-sm text-muted-foreground">
                  Upgrade your account to generate exposure reports, risk assessments, and trend analysis with AI insights.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Report Type */}
                <div>
                  <label className="block text-sm text-muted-foreground mb-2">Report Type</label>
                  <div className="grid grid-cols-3 gap-2">
                    {['Exposure', 'Risk', 'Trend'].map((type) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setReportType(type)}
                        className={`p-3 rounded-lg text-sm transition-all ${
                          reportType === type
                            ? 'bg-tech-blue-500/40 border border-tech-blue-500 text-tech-blue-300'
                            : 'bg-white/5 border border-white/10 text-muted-foreground hover:border-tech-blue-500/30'
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Pollutant Selection */}
                <div>
                  <label className="block text-sm text-muted-foreground mb-2">Pollutant</label>
                  <select
                    value={pollutant}
                    onChange={(e) => setPollutant(e.target.value)}
                    title="Select pollutant type"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-tech-blue-500/50"
                  >
                    <option>PM25</option>
                    <option>PM10</option>
                    <option>NO2</option>
                    <option>SO2</option>
                    <option>O3</option>
                  </select>
                </div>

                {/* District Selection */}
                <div>
                  <label className="block text-sm text-muted-foreground mb-2">Select District</label>
                  {isLoadingDistricts ? (
                    <div className="flex items-center justify-center p-3 bg-white/5 rounded-lg">
                      <Loader className="w-4 h-4 animate-spin text-tech-blue-500" />
                    </div>
                  ) : (
                    <select
                      value={selectedDistrict}
                      onChange={(e) => setSelectedDistrict(e.target.value)}
                      title="Select a district"
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-tech-blue-500/50"
                    >
                      {districts.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.district_name || d.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {/* Date Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-muted-foreground mb-2">Start Date</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      title="Select start date"
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-tech-blue-500/50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-muted-foreground mb-2">End Date</label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      title="Select end date"
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-tech-blue-500/50"
                    />
                  </div>
                </div>

                {/* Generate Button */}
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 bg-tech-blue-500/20 hover:bg-tech-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed border border-tech-blue-500/50 rounded-lg text-tech-blue-400 font-semibold transition-all flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader size={18} className="animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Zap size={18} />
                      Generate Report
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </motion.div>

        {/* Recent Reports */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-1"
        >
          <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-foreground font-mono mb-4">Recent Reports</h3>

            {isLoadingReports ? (
              <div className="flex items-center justify-center p-8">
                <Loader className="w-6 h-6 animate-spin text-tech-blue-500" />
              </div>
            ) : reports.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No reports generated yet
              </p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {reports.map((report) => (
                  <motion.div
                    key={report.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="p-3 bg-white/5 rounded-lg border border-white/10 hover:border-tech-blue-500/30 transition-all cursor-pointer group"
                  >
                    <div className="flex items-start justify-between mb-1">
                      <p className="text-sm text-foreground group-hover:text-tech-blue-300">
                        {report.title}
                      </p>
                      <button
                        onClick={() => handleDownload(report.id)}
                        className="text-muted-foreground hover:text-tech-blue-400 transition-colors"
                        title="Download report"
                      >
                        <DownloadCloud size={16} />
                      </button>
                    </div>
                    <p className="text-xs text-muted-foreground">{report.district_name}</p>
                    <p className="text-xs text-muted-foreground/70">
                      {new Date(report.created_at).toLocaleDateString()}
                    </p>
                  </motion.div>
                ))}
              </div>
            )}

            {!isPremium && (
              <div className="mt-4 p-3 bg-neon-green-500/10 border border-neon-green-500/30 rounded-lg">
                <p className="text-xs text-neon-green-400">
                  ⭐ Upgrade to Premium for unlimited reports with AI insights
                </p>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
