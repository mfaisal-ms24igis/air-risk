/**
 * Report Store - Zustand
 * 
 * Global state for report generation and management.
 * Handles async report creation, polling, and download history.
 * 
 * @module store/reportStore
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  Report,
  ReportStatus,
  CreateLocationReportRequest,
  CreateLocationReportResponse,
  ReportStatusResponse,
  ListReportsResponse,
} from '@/types/reports';

// =============================================================================
// Types
// =============================================================================

export interface ReportGenerationState {
  isGenerating: boolean;
  currentReportId: number | null;
  progress: number; // 0-100
  estimatedTimeRemaining: number; // seconds
  error: string | null;
}

export interface ReportStore {
  // State
  reports: Report[];
  generationState: ReportGenerationState;
  pollingIntervalId: number | null;

  // Actions
  createLocationReport: (request: CreateLocationReportRequest, accessToken: string) => Promise<CreateLocationReportResponse>;
  pollReportStatus: (reportId: number, accessToken: string) => Promise<void>;
  startPolling: (reportId: number, accessToken: string) => void;
  stopPolling: () => void;
  fetchReports: (accessToken: string, status?: ReportStatus) => Promise<void>;
  downloadReport: (reportId: number) => void;
  deleteReport: (reportId: number) => void;
  clearError: () => void;
  reset: () => void;
}

// =============================================================================
// Initial State
// =============================================================================

const initialGenerationState: ReportGenerationState = {
  isGenerating: false,
  currentReportId: null,
  progress: 0,
  estimatedTimeRemaining: 0,
  error: null,
};

// =============================================================================
// Store
// =============================================================================

export const useReportStore = create<ReportStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        reports: [],
        generationState: initialGenerationState,
        pollingIntervalId: null,

        // Create location report
        createLocationReport: async (request, accessToken) => {
          set({
            generationState: {
              isGenerating: true,
              currentReportId: null,
              progress: 10,
              estimatedTimeRemaining: 30,
              error: null,
            },
          });

          try {
            // Use new async report generation endpoint
            const response = await fetch('/api/v1/reports/generate/', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`,
              },
              body: JSON.stringify({
                report_type: 'LOCATION',
                parameters: request,
              }),
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              const errorMessage = errorData.error?.message || errorData.error || 'Failed to create report';

              // Check for tier restrictions
              if (errorData.error?.code === 'tier_restriction' || errorData.error?.code === 'quota_exceeded') {
                throw new Error(errorMessage + ' Please upgrade your subscription.');
              }

              throw new Error(errorMessage);
            }

            const data = await response.json();

            set((state) => ({
              generationState: {
                ...state.generationState,
                currentReportId: data.report_id,
                progress: 20,
                estimatedTimeRemaining: 60, // Default estimate
              },
            }));

            // Start polling for async task
            get().startPolling(data.report_id, accessToken);

            return {
              report_id: data.report_id,
              task_id: data.task_id,
              status: data.status,
              poll_url: data.poll_url,
              tier: 'BASIC', // Default tier
            } as CreateLocationReportResponse;

          } catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            set({
              generationState: {
                ...initialGenerationState,
                error: message,
              },
            });
            throw error;
          }
        },

        // Poll report status
        pollReportStatus: async (reportId, accessToken) => {
          try {
            // Use new async status endpoint
            const statusResponse = await fetch(`/api/v1/reports/${reportId}/status/`, {
              headers: {
                'Authorization': `Bearer ${accessToken}`,
              },
            });

            if (!statusResponse.ok) {
              throw new Error('Failed to fetch report status');
            }

            const data: ReportStatusResponse = await statusResponse.json();

            // Update progress based on status
            let progress = get().generationState.progress;
            if (data.status === 'processing' && progress < 90) {
              progress = Math.min(90, progress + 10);
            } else if (data.status === 'completed') {
              progress = 100;
            }

            // Update estimated time if provided
            const estimatedTimeRemaining = data.estimated_seconds || 0;

            set((state) => ({
              generationState: {
                ...state.generationState,
                progress,
                estimatedTimeRemaining,
              },
            }));

            // If completed or failed, stop polling
            if (data.status === 'completed' || data.status === 'failed') {
              get().stopPolling();

              if (data.status === 'completed') {
                set({
                  generationState: {
                    isGenerating: false,
                    currentReportId: reportId,
                    progress: 100,
                    estimatedTimeRemaining: 0,
                    error: null,
                  },
                });

                // Refresh report list
                await get().fetchReports(accessToken);
              } else {
                set({
                  generationState: {
                    ...initialGenerationState,
                    error: data.error || 'Report generation failed',
                  },
                });
              }
            }

          } catch (error) {
            console.error('Polling error:', error);
            // Don't stop polling on transient errors
          }
        },

        // Start polling
        startPolling: (reportId, accessToken) => {
          // Clear existing interval
          get().stopPolling();

          // Poll every 3 seconds
          const intervalId = window.setInterval(() => {
            get().pollReportStatus(reportId, accessToken);
          }, 3000);

          set({ pollingIntervalId: intervalId });

          // Initial poll
          get().pollReportStatus(reportId, accessToken);
        },

        // Stop polling
        stopPolling: () => {
          const { pollingIntervalId } = get();
          if (pollingIntervalId) {
            clearInterval(pollingIntervalId);
            set({ pollingIntervalId: null });
          }
        },

        // Fetch reports
        fetchReports: async (accessToken, status) => {
          try {
            let url = '/api/v1/reports/';
            if (status) {
              url += `?status=${status}`;
            }

            const response = await fetch(url, {
              headers: {
                'Authorization': `Bearer ${accessToken}`,
              },
            });

            if (!response.ok) {
              throw new Error('Failed to fetch reports');
            }

            const data: ListReportsResponse = await response.json();

            // Handle new API response format
            const reports = data.results || data.reports || [];
            set({ reports });

          } catch (error) {
            console.error('Failed to fetch reports:', error);
          }
        },

        // Download report
        downloadReport: (reportId) => {
          const report = get().reports.find((r) => r.id === reportId);
          if (report?.download_url) {
            window.open(report.download_url, '_blank');
          }
        },

        // Delete report
        deleteReport: (reportId) => {
          set((state) => ({
            reports: state.reports.filter((r) => r.id !== reportId),
          }));
        },

        // Clear error
        clearError: () => {
          set((state) => ({
            generationState: {
              ...state.generationState,
              error: null,
            },
          }));
        },

        // Reset
        reset: () => {
          get().stopPolling();
          set({
            reports: [],
            generationState: initialGenerationState,
            pollingIntervalId: null,
          });
        },
      }),
      {
        name: 'report-storage',
        partialize: (state) => ({
          reports: state.reports,
        }),
      }
    ),
    { name: 'ReportStore' }
  )
);

// =============================================================================
// Hooks (Selectors)
// =============================================================================

export const useReports = () => useReportStore((state) => state.reports);
export const useGenerationState = () => useReportStore((state) => state.generationState);
export const useIsGenerating = () => useReportStore((state) => state.generationState.isGenerating);
