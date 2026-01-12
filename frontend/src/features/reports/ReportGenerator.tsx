import { useState } from 'react';
import { useUserTier } from '@/hooks/useUserTier';
import { FileText, Download, Loader2, MapPin, Calendar, Sparkles } from 'lucide-react';
import { cn, formatDateForApi, daysBetween } from '@/lib/utils';
import axios from 'axios';

interface ReportGeneratorProps {
  userLocation?: { lat: number; lng: number };
  districtId?: string;
  districtName?: string;
  className?: string;
}

interface ReportFormData {
  startDate: string;
  endDate: string;
  location?: { lat: number; lng: number };
  reportType: 'location' | 'district';
}

export function ReportGenerator({
  userLocation,
  districtId,
  districtName,
  className = '',
}: ReportGeneratorProps) {
  const { features, tier } = useUserTier();
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState<string>('');
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Default to last 7 days
  const today = new Date();
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  const [formData, setFormData] = useState<ReportFormData>({
    startDate: formatDateForApi(weekAgo),
    endDate: formatDateForApi(today),
    location: userLocation,
    reportType: userLocation ? 'location' : 'district',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setReportUrl(null);

    // Validate date range
    const start = new Date(formData.startDate);
    const end = new Date(formData.endDate);
    const days = daysBetween(start, end);

    if (days > features.maxReportDays) {
      setError(`Date range cannot exceed ${features.maxReportDays} days for ${tier} tier`);
      return;
    }

    if (start > end) {
      setError('Start date must be before end date');
      return;
    }

    setIsGenerating(true);

    try {
      // Get auth token
      const token = localStorage.getItem('access_token');

      if (!token) {
        throw new Error('Authentication required');
      }

      setGenerationStep('Analyzing air quality data...');

      const payload: any = {
        report_type: formData.reportType,
        start_date: formData.startDate,
        end_date: formData.endDate,
      };

      if (formData.reportType === 'location' && formData.location) {
        payload.location = {
          lat: formData.location.lat,
          lng: formData.location.lng,
          radius: 5000, // 5km radius
        };
      } else if (formData.reportType === 'district' && districtId) {
        payload.district_id = districtId;
      }

      setGenerationStep('Calculating exposure metrics...');

      // Make API request
      const response = await axios.post(
        'http://127.0.0.1:8000/api/v1/reports/reports/',
        payload,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      setGenerationStep('Generating AI insights...');

      // For PREMIUM users, report generation is async
      if (tier === 'PREMIUM') {
        // Poll for report completion
        const reportId = response.data.id;
        let attempts = 0;
        const maxAttempts = 60; // 60 seconds max

        const pollInterval = setInterval(async () => {
          attempts++;

          if (attempts > maxAttempts) {
            clearInterval(pollInterval);
            setError('Report generation timed out. Please check your reports list.');
            setIsGenerating(false);
            return;
          }

          try {
            const statusResponse = await axios.get(
              `http://127.0.0.1:8000/api/v1/reports/reports/${reportId}/`,
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            );

            if (statusResponse.data.status === 'completed') {
              clearInterval(pollInterval);
              setReportUrl(statusResponse.data.file);
              setIsGenerating(false);
              setGenerationStep('');
            } else if (statusResponse.data.status === 'failed') {
              clearInterval(pollInterval);
              setError('Report generation failed');
              setIsGenerating(false);
              setGenerationStep('');
            } else {
              setGenerationStep(`Processing... (${attempts}s)`);
            }
          } catch (err) {
            console.error('Polling error:', err);
          }
        }, 1000);
      } else {
        // BASIC users get synchronous generation
        setGenerationStep('Creating PDF...');
        setReportUrl(response.data.file);
        setIsGenerating(false);
        setGenerationStep('');
      }
    } catch (err: any) {
      console.error('Report generation error:', err);
      setError(err.response?.data?.error || 'Failed to generate report');
      setIsGenerating(false);
      setGenerationStep('');
    }
  };

  const handleDownload = () => {
    if (reportUrl) {
      window.open(`http://127.0.0.1:8000${reportUrl}`, '_blank');
    }
  };

  if (!features.canGenerateCustomReports) {
    return null;
  }

  return (
    <div className={cn('bg-white rounded-lg shadow-elevation-2 p-6', className)}>
      <div className="flex items-center gap-2 mb-4">
        <FileText className="h-5 w-5 text-brand-primary" />
        <h3 className="font-semibold text-lg">Generate Custom Report</h3>
        {tier === 'PREMIUM' && (
          <span className="ml-auto flex items-center gap-1 text-xs bg-brand-primary text-white px-2 py-1 rounded">
            <Sparkles className="h-3 w-3" />
            AI Insights
          </span>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Report Type */}
        <div>
          <label className="block text-sm font-medium mb-1">Report Type</label>
          <div className="grid grid-cols-2 gap-2">
            {userLocation && (
              <button
                type="button"
                onClick={() => setFormData({ ...formData, reportType: 'location' })}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded border transition-colors',
                  formData.reportType === 'location'
                    ? 'border-brand-primary bg-brand-primary/10 text-brand-primary'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <MapPin className="h-4 w-4" />
                <span className="text-sm">My Location</span>
              </button>
            )}
            {districtId && (
              <button
                type="button"
                onClick={() => setFormData({ ...formData, reportType: 'district' })}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded border transition-colors',
                  formData.reportType === 'district'
                    ? 'border-brand-primary bg-brand-primary/10 text-brand-primary'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <FileText className="h-4 w-4" />
                <span className="text-sm">{districtName || 'District'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Date Range */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Start Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="date"
                value={formData.startDate}
                onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                max={formData.endDate}
                className="w-full pl-10 pr-3 py-2 border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-brand-primary"
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">End Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="date"
                value={formData.endDate}
                onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                min={formData.startDate}
                max={formatDateForApi(today)}
                className="w-full pl-10 pr-3 py-2 border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-brand-primary"
                required
              />
            </div>
          </div>
        </div>

        {/* Helper text */}
        <p className="text-xs text-muted-foreground">
          Maximum range: {features.maxReportDays} days for {tier} tier
          {tier === 'PREMIUM' && ' • Includes AI-powered insights and recommendations'}
        </p>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        {/* Generation Progress */}
        {isGenerating && generationStep && (
          <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded text-sm flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            {generationStep}
          </div>
        )}

        {/* Success */}
        {reportUrl && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
            <p className="text-sm font-medium mb-2">Report generated successfully!</p>
            <button
              type="button"
              onClick={handleDownload}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors text-sm"
            >
              <Download className="h-4 w-4" />
              Download PDF Report
            </button>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isGenerating}
          className={cn(
            'w-full flex items-center justify-center gap-2 bg-brand-primary text-white px-6 py-3 rounded font-medium transition-colors',
            isGenerating
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:bg-brand-primary/90'
          )}
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Generating Report...
            </>
          ) : (
            <>
              <FileText className="h-5 w-5" />
              Generate Report
            </>
          )}
        </button>
      </form>
    </div>
  );
}
