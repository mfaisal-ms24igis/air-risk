/**
 * ReportHistory Component
 * 
 * Display list of user's generated reports with download/delete actions.
 * Auto-refreshes to show latest reports.
 * 
 * @module components/reports/ReportHistory
 */

import { useEffect } from 'react';
import { useAuthStore, useReportStore, useReports } from '@/store';
import type { Report } from '@/types/reports';

// =============================================================================
// Component
// =============================================================================

export function ReportHistory() {
  const { accessToken } = useAuthStore();
  const { fetchReports, downloadReport, deleteReport } = useReportStore();
  const reports = useReports();

  // Fetch reports on mount
  useEffect(() => {
    if (accessToken) {
      fetchReports(accessToken);
    }
  }, [accessToken, fetchReports]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    if (!accessToken) return;

    const intervalId = setInterval(() => {
      fetchReports(accessToken);
    }, 10000);

    return () => clearInterval(intervalId);
  }, [accessToken, fetchReports]);

  // =============================================================================
  // Helpers
  // =============================================================================

  function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function getStatusBadge(status: Report['status']) {
    const styles = {
      completed: 'bg-green-100 text-green-800',
      processing: 'bg-blue-100 text-blue-800',
      pending: 'bg-yellow-100 text-yellow-800',
      failed: 'bg-red-100 text-red-800',
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  }

  // =============================================================================
  // Render
  // =============================================================================

  if (!accessToken) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <p className="text-center text-gray-600">Please log in to view your reports</p>
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Your Reports</h2>
        <div className="text-center py-12">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="mt-4 text-gray-600">No reports yet</p>
          <p className="mt-2 text-sm text-gray-500">
            Generate your first location-based air quality report above
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-gray-900">Your Reports</h2>
        <button
          onClick={() => accessToken && fetchReports(accessToken)}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          🔄 Refresh
        </button>
      </div>

      <div className="space-y-4">
        {reports.map((report) => (
          <div
            key={report.id}
            className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-sm font-semibold text-gray-900">{report.title}</h3>
                  {getStatusBadge(report.status)}
                </div>

                <div className="space-y-1 text-xs text-gray-600">
                  <p>
                    <span className="font-medium">Created:</span> {formatDate(report.created_at)}
                  </p>

                  {report.completed_at && (
                    <p>
                      <span className="font-medium">Completed:</span> {formatDate(report.completed_at)}
                    </p>
                  )}

                  {report.expires_at && (
                    <p>
                      <span className="font-medium">Expires:</span> {formatDate(report.expires_at)}
                    </p>
                  )}

                  {report.file_size_kb && (
                    <p>
                      <span className="font-medium">Size:</span> {report.file_size_kb.toFixed(1)} KB
                    </p>
                  )}

                  {report.error && (
                    <p className="text-red-600">
                      <span className="font-medium">Error:</span> {report.error}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 ml-4">
                {report.status === 'completed' && report.download_url && (
                  <button
                    onClick={() => downloadReport(report.id)}
                    className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 transition-colors"
                  >
                    📥 Download
                  </button>
                )}

                {report.status === 'processing' && (
                  <div className="flex items-center gap-2 text-xs text-blue-600">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    <span>Processing...</span>
                  </div>
                )}

                <button
                  onClick={() => deleteReport(report.id)}
                  className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                  title="Delete report"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {reports.length > 5 && (
        <p className="mt-4 text-xs text-center text-gray-500">
          Showing {reports.length} reports • Auto-refreshing every 10s
        </p>
      )}
    </div>
  );
}

export default ReportHistory;
