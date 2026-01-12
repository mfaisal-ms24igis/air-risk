/**
 * API Service Layer
 * 
 * Centralized API client with automatic Django envelope unwrapping.
 * All API calls should go through this module for consistent error handling.
 * 
 * Features:
 * - Automatic unwrapping of Django { status, data, message } envelope
 * - Type-safe request/response handling
 * - Centralized error normalization
 * - Request/response logging in development
 * 
 * @module services/api
 */

import axios, {
  AxiosInstance,
  AxiosError,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
} from 'axios';
import type { ApiResponse, ApiError, ApiSuccessResponse } from '@/types/api';

// =============================================================================
// Configuration
// =============================================================================

/**
 * API base URL from environment or default
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Request timeout in milliseconds
 */
const REQUEST_TIMEOUT = 30_000;

// =============================================================================
// Error Handling
// =============================================================================

/**
 * Get user-friendly error message based on HTTP status code
 */
function getErrorMessage(status: number): string {
  const messages: Record<number, string> = {
    400: 'Invalid request. Please check your input.',
    401: 'Authentication required. Please log in.',
    403: 'You do not have permission to perform this action.',
    404: 'The requested resource was not found.',
    408: 'Request timed out. Please try again.',
    429: 'Too many requests. Please wait a moment.',
    500: 'Server error. Please try again later.',
    502: 'Server is temporarily unavailable.',
    503: 'Service unavailable. Please try again later.',
  };
  return messages[status] || 'An unexpected error occurred.';
}

/**
 * Normalize any error into a consistent ApiError structure
 */
function normalizeError(error: unknown): ApiError {
  const timestamp = new Date().toISOString();

  // Handle Axios errors
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiResponse>;

    // Network error (no response)
    if (!axiosError.response) {
      return {
        status: 'error',
        message: axiosError.message === 'Network Error'
          ? 'Unable to connect to server. Please check your network.'
          : axiosError.message,
        code: 'NETWORK_ERROR',
        timestamp,
        originalError: error,
      };
    }

    const { status, data } = axiosError.response;

    // Django error response with message
    if (data && typeof data === 'object' && 'message' in data) {
      return {
        status: 'error',
        message: data.message || getErrorMessage(status),
        code: `HTTP_${status}`,
        statusCode: status,
        errors: (data as ApiResponse & { errors?: Record<string, string[]> }).errors,
        timestamp,
        originalError: error,
      };
    }

    // Generic HTTP error
    return {
      status: 'error',
      message: getErrorMessage(status),
      code: `HTTP_${status}`,
      statusCode: status,
      timestamp,
      originalError: error,
    };
  }

  // Handle standard Error objects
  if (error instanceof Error) {
    return {
      status: 'error',
      message: error.message,
      code: 'UNKNOWN_ERROR',
      timestamp,
      originalError: error,
    };
  }

  // Handle string errors
  if (typeof error === 'string') {
    return {
      status: 'error',
      message: error,
      code: 'UNKNOWN_ERROR',
      timestamp,
    };
  }

  // Fallback for unknown error types
  return {
    status: 'error',
    message: 'An unexpected error occurred.',
    code: 'UNKNOWN_ERROR',
    timestamp,
    originalError: error,
  };
}

/**
 * Log error in development
 */
function logError(error: ApiError, context?: string): void {
  if (import.meta.env.DEV) {
    const prefix = context ? `[API ${context}]` : '[API Error]';
    console.error(`${prefix}`, {
      message: error.message,
      code: error.code,
      statusCode: error.statusCode,
      errors: error.errors,
    });
  }

  // TODO: In production, send to error tracking service
  // if (import.meta.env.PROD) {
  //   Sentry.captureException(error.originalError || error);
  // }
}

// =============================================================================
// Axios Instance
// =============================================================================

/**
 * Create and configure the Axios instance
 */
function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: REQUEST_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  });

  // Request interceptor
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Add auth token if available
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Log request in development
      if (import.meta.env.DEV) {
        console.debug(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
          params: config.params,
          data: config.data,
        });
      }

      return config;
    },
    (error) => {
      const normalized = normalizeError(error);
      logError(normalized, 'Request');
      return Promise.reject(normalized);
    }
  );

  // Response interceptor - UNWRAPS the Django envelope
  client.interceptors.response.use(
    (response) => {
      const envelope = response.data as ApiResponse;

      // Log response in development
      if (import.meta.env.DEV) {
        console.debug(`[API Response] ${response.config.url}`, {
          status: envelope.status,
          message: envelope.message,
        });
      }

      // Check if response follows Django envelope format
      if (envelope && typeof envelope === 'object' && 'status' in envelope) {
        if (envelope.status === 'success') {
          // UNWRAP: Return only the data portion
          return (envelope as ApiSuccessResponse).data;
        }

        // Error response from Django
        const error = normalizeError({
          response: {
            status: response.status,
            data: envelope,
          },
        } as AxiosError<ApiResponse>);
        logError(error, 'Response');
        return Promise.reject(error);
      }

      // Non-envelope response (raw data) - return as-is
      return response.data;
    },
    (error: AxiosError<ApiResponse>) => {
      const normalized = normalizeError(error);
      logError(normalized, 'Response');
      return Promise.reject(normalized);
    }
  );

  return client;
}

/**
 * Singleton API client instance
 */
export const apiClient = createApiClient();

// =============================================================================
// Type-Safe Request Methods
// =============================================================================

/**
 * GET request with automatic envelope unwrapping
 * 
 * @template T - Expected response data type (after unwrapping)
 * @param url - API endpoint (relative to base URL)
 * @param params - Query parameters
 * @param config - Additional Axios config
 * @returns Promise resolving to unwrapped data
 * 
 * @example
 * ```typescript
 * const stations = await api.get<AirQualityStation[]>('/stations/');
 * const district = await api.get<District>('/districts/1/');
 * ```
 */
export async function get<T>(
  url: string,
  params?: Record<string, unknown>,
  config?: AxiosRequestConfig
): Promise<T> {
  return apiClient.get<T, T>(url, { ...config, params });
}

/**
 * POST request with automatic envelope unwrapping
 */
export async function post<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  return apiClient.post<T, T>(url, data, config);
}

/**
 * PUT request with automatic envelope unwrapping
 */
export async function put<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  return apiClient.put<T, T>(url, data, config);
}

/**
 * PATCH request with automatic envelope unwrapping
 */
export async function patch<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  return apiClient.patch<T, T>(url, data, config);
}

/**
 * DELETE request with automatic envelope unwrapping
 */
export async function del<T>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  return apiClient.delete<T, T>(url, config);
}

// =============================================================================
// API Module Export
// =============================================================================

/**
 * Default export as namespace for convenient importing
 * 
 * @example
 * ```typescript
 * import api from '@/services/api';
 * 
 * const stations = await api.get<Station[]>('/stations/');
 * ```
 */
const api = {
  client: apiClient,
  get,
  post,
  put,
  patch,
  delete: del,
};

export default api;
