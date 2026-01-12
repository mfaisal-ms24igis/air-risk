/**
 * Report Types
 * 
 * Type definitions for location-based air quality reports.
 */

export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type ReportType = 'LOCATION' | 'DISTRICT' | 'PROVINCE';

export interface Report {
  id: number;
  type: ReportType;
  title: string;
  status: ReportStatus;
  created_at: string;
  completed_at?: string;
  download_url?: string;
  file_size_kb?: number;
  expires_at?: string;
  error?: string;
}

export interface CreateLocationReportRequest {
  lat: number;
  lng: number;
  radius_km: number;
  start_date: string;
  end_date: string;
  include_ai?: boolean;
}

export interface CreateLocationReportResponse {
  report_id: number;
  status: ReportStatus;
  download_url?: string;
  file_size_kb?: number;
  poll_url?: string;
  estimated_time_seconds?: number;
  tier: string;
  include_ai?: boolean;
}

export interface ReportStatusResponse {
  report_id: number;
  status: ReportStatus;
  download_url?: string;
  file_size_kb?: number;
  created_at: string;
  completed_at?: string;
  expires_at?: string;
  error?: string;
  estimated_seconds?: number;
}

export interface ListReportsResponse {
  count: number;
  tier: string;
  reports: Report[];
  results?: Report[];
}
