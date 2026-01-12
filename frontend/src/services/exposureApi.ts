/**
 * Exposure API Service
 * 
 * API client for exposure analytics endpoints.
 * Uses a separate base URL from the air-quality API.
 * 
 * @module services/exposureApi
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import type { ApiResponse, ApiSuccessResponse, ApiError } from '@/types/api';

// =============================================================================
// Configuration
// =============================================================================

const EXPOSURE_API_URL = import.meta.env.VITE_EXPOSURE_API_URL || '/api/v1/exposure';
const REQUEST_TIMEOUT = 30_000;

// =============================================================================
// Error Handling (shared with main api.ts)
// =============================================================================

function normalizeError(error: unknown): ApiError {
  const timestamp = new Date().toISOString();

  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return {
        status: 'error',
        message: 'Unable to connect to server.',
        code: 'NETWORK_ERROR',
        timestamp,
      };
    }
    const { status, data } = error.response;
    return {
      status: 'error',
      message: (data as ApiResponse)?.message || `HTTP Error ${status}`,
      code: `HTTP_${status}`,
      statusCode: status,
      timestamp,
    };
  }

  return {
    status: 'error',
    message: error instanceof Error ? error.message : 'Unknown error',
    code: 'UNKNOWN_ERROR',
    timestamp,
  };
}

// =============================================================================
// Axios Instance
// =============================================================================

function createExposureClient(): AxiosInstance {
  const client = axios.create({
    baseURL: EXPOSURE_API_URL,
    timeout: REQUEST_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  });

  // Response interceptor - unwraps Django envelope
  client.interceptors.response.use(
    (response) => {
      const envelope = response.data as ApiResponse;

      if (import.meta.env.DEV) {
        console.debug(`[Exposure API] ${response.config.url}`, {
          status: envelope.status,
          message: envelope.message,
        });
      }

      if (envelope && typeof envelope === 'object' && 'status' in envelope) {
        if (envelope.status === 'success') {
          return (envelope as ApiSuccessResponse).data;
        }
        return Promise.reject(normalizeError({ response }));
      }

      return response.data;
    },
    (error) => {
      return Promise.reject(normalizeError(error));
    }
  );

  return client;
}

export const exposureClient = createExposureClient();

// =============================================================================
// Type-Safe Request Methods
// =============================================================================

export async function get<T>(
  url: string,
  params?: Record<string, unknown>,
  config?: AxiosRequestConfig
): Promise<T> {
  return exposureClient.get<T, T>(url, { ...config, params });
}

export async function post<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  return exposureClient.post<T, T>(url, data, config);
}

// =============================================================================
// Export
// =============================================================================

const exposureApi = {
  client: exposureClient,
  get,
  post,
};

export default exposureApi;
