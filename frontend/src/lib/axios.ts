/**
 * Axios Instance Configuration
 * 
 * Enterprise-grade HTTP client with:
 * - Global error logging
 * - Request/response interceptors
 * - Automatic JSON transformation
 * - Type-safe response unwrapping
 * 
 * @module lib/axios
 */

import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';

// =============================================================================
// Types
// =============================================================================

/**
 * Standard API response envelope from Django REST Framework
 */
export interface ApiEnvelope<T = unknown> {
  status: 'success' | 'error';
  data: T;
  message: string;
}

/**
 * Normalized error structure for consistent error handling
 */
export interface ApiError {
  status: 'error';
  message: string;
  code?: string;
  statusCode?: number;
  errors?: Record<string, string[]>;
  timestamp: string;
}

// =============================================================================
// Error Logging
// =============================================================================

/**
 * Centralized error logger
 * In production, this could send to Sentry, DataDog, etc.
 */
function logError(error: ApiError, context?: string): void {
  const prefix = context ? `[${context}]` : '[API Error]';

  console.error(`${prefix} ${error.message}`, {
    code: error.code,
    statusCode: error.statusCode,
    timestamp: error.timestamp,
    errors: error.errors,
  });

  // TODO: In production, send to error tracking service
  // if (import.meta.env.PROD) {
  //   Sentry.captureException(error);
  // }
}

/**
 * Transform AxiosError into normalized ApiError
 */
function normalizeError(error: AxiosError<ApiEnvelope>): ApiError {
  const timestamp = new Date().toISOString();

  // Network error (no response)
  if (!error.response) {
    return {
      status: 'error',
      message: error.message === 'Network Error'
        ? 'Unable to connect to server. Please check your network connection.'
        : error.message,
      code: 'NETWORK_ERROR',
      timestamp,
    };
  }

  const { status, data } = error.response;

  // Handle Django REST Framework error format
  if (data && typeof data === 'object') {
    // 1. Envelope format ({ status: 'error', message: '...', errors: ... })
    if ('message' in data) {
      return {
        status: 'error',
        message: data.message || getDefaultMessage(status),
        code: `HTTP_${status}`,
        statusCode: status,
        errors: (data as ApiEnvelope & { errors?: Record<string, string[]> }).errors,
        timestamp,
      };
    }

    // 2. Raw DRF Validation Errors (e.g. { field: ["Error"] })
    // Assume if 400 and has keys, it's a validation error map
    if (status === 400) {
      const errors = data as Record<string, string[] | string>;
      // Construct a readable message from the first error
      const firstKey = Object.keys(errors)[0];
      const firstVal = errors[firstKey];
      const firstMsg = Array.isArray(firstVal) ? firstVal[0] : String(firstVal);

      return {
        status: 'error',
        message: firstMsg || 'Validation failed',
        code: 'VALIDATION_ERROR',
        statusCode: status,
        errors: errors as Record<string, string[]>,
        timestamp
      };
    }
  }

  // Fallback for non-standard errors
  return {
    status: 'error',
    message: getDefaultMessage(status),
    code: `HTTP_${status}`,
    statusCode: status,
    timestamp,
  };
}

/**
 * Default error messages by HTTP status code
 */
function getDefaultMessage(status: number): string {
  const messages: Record<number, string> = {
    400: 'Invalid request. Please check your input.',
    401: 'Authentication required. Please log in.',
    403: 'Access denied. You do not have permission.',
    404: 'Resource not found.',
    408: 'Request timeout. Please try again.',
    429: 'Too many requests. Please wait before retrying.',
    500: 'Server error. Our team has been notified.',
    502: 'Service temporarily unavailable.',
    503: 'Service under maintenance. Please try again later.',
    504: 'Gateway timeout. Please try again.',
  };

  return messages[status] || `Unexpected error (${status})`;
}

// =============================================================================
// Axios Instance
// =============================================================================

/**
 * Pre-configured Axios instance for API requests
 * 
 * Features:
 * - Base URL from Vite proxy (/api)
 * - 30-second timeout
 * - Automatic response envelope unwrapping
 * - Global error logging
 * - Bearer token injection (when available)
 */
const api: AxiosInstance = axios.create({
  baseURL: '/api/v1/air-quality',
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// =============================================================================
// Request Interceptor
// =============================================================================

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Inject auth token if available
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Log outgoing requests in development
    if (import.meta.env.DEV) {
      console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`, {
        params: config.params,
      });
    }

    return config;
  },
  (error: AxiosError<ApiEnvelope>) => {
    const apiError = normalizeError(error);
    logError(apiError, 'Request');
    return Promise.reject(apiError);
  }
);

// =============================================================================
// Response Interceptor
// =============================================================================

api.interceptors.response.use(
  (response: AxiosResponse<ApiEnvelope>) => {
    const { data } = response;

    // Handle standard envelope format: { status, data, message }
    if (data && typeof data === 'object' && 'status' in data) {
      if (data.status === 'success') {
        // Unwrap and return only the data payload
        return data.data as AxiosResponse['data'];
      }

      // API returned error status
      const apiError: ApiError = {
        status: 'error',
        message: data.message || 'Request failed',
        code: 'API_ERROR',
        statusCode: response.status,
        timestamp: new Date().toISOString(),
      };
      logError(apiError, 'Response');
      return Promise.reject(apiError);
    }

    // Non-envelope response (e.g., raw GeoJSON) - return as-is
    return data;
  },
  (error: AxiosError<ApiEnvelope>) => {
    const apiError = normalizeError(error);
    logError(apiError, 'Response');
    return Promise.reject(apiError);
  }
);

// =============================================================================
// Typed Request Helpers
// =============================================================================

/**
 * Type-safe GET request
 */
export async function get<T>(
  url: string,
  params?: Record<string, unknown>
): Promise<T> {
  return api.get<T, T>(url, { params });
}

/**
 * Type-safe POST request
 */
export async function post<T, D = unknown>(
  url: string,
  data?: D
): Promise<T> {
  return api.post<T, T>(url, data);
}

/**
 * Type-safe PUT request
 */
export async function put<T, D = unknown>(
  url: string,
  data?: D
): Promise<T> {
  return api.put<T, T>(url, data);
}

/**
 * Type-safe PATCH request
 */
export async function patch<T, D = unknown>(
  url: string,
  data?: D
): Promise<T> {
  return api.patch<T, T>(url, data);
}

/**
 * Type-safe DELETE request
 */
export async function del<T = void>(url: string): Promise<T> {
  return api.delete<T, T>(url);
}

// Export instance for advanced use cases
export { api };
export default api;
