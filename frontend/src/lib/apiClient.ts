/**
 * API Interceptor with Automatic Token Refresh
 * 
 * Wraps fetch to automatically:
 * - Add Authorization header
 * - Refresh expired tokens
 * - Retry failed requests after token refresh
 * - Handle rate limiting errors with tier information
 */

import { useAuthStore } from '@/store/authStore';

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  retry_after?: number;
  current_tier?: string;
  upgrade_available?: boolean;
}

export class ApiException extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public error?: ApiError
  ) {
    super(message);
    this.name = 'ApiException';
  }
}

/**
 * Enhanced fetch with automatic token refresh
 */
export async function apiFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const { accessToken, refreshAccessToken, logout } = useAuthStore.getState();
  
  // Add Authorization header if token exists
  const headers = new Headers(options.headers);
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  
  // Make request
  let response = await fetch(url, {
    ...options,
    headers,
  });
  
  // If 401 Unauthorized, try to refresh token and retry
  if (response.status === 401 && accessToken) {
    try {
      // Attempt token refresh
      await refreshAccessToken();
      
      // Retry request with new token
      const newAccessToken = useAuthStore.getState().accessToken;
      if (newAccessToken) {
        headers.set('Authorization', `Bearer ${newAccessToken}`);
        response = await fetch(url, {
          ...options,
          headers,
        });
      }
    } catch (refreshError) {
      // Refresh failed, logout user
      logout();
      throw new ApiException('Session expired. Please log in again.', 401);
    }
  }
  
  // Handle error responses
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const apiError: ApiError | undefined = errorData.error;
    
    // Construct error message
    let message = 'Request failed';
    if (apiError?.message) {
      message = apiError.message;
    } else if (errorData.detail) {
      message = errorData.detail;
    } else if (errorData.message) {
      message = errorData.message;
    }
    
    throw new ApiException(message, response.status, apiError);
  }
  
  return response;
}

/**
 * Type-safe API request helper
 */
export async function apiRequest<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await apiFetch(url, options);
  return response.json();
}

/**
 * GET request helper
 */
export async function apiGet<T>(url: string): Promise<T> {
  return apiRequest<T>(url, { method: 'GET' });
}

/**
 * POST request helper
 */
export async function apiPost<T>(url: string, data: any): Promise<T> {
  return apiRequest<T>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

/**
 * PUT request helper
 */
export async function apiPut<T>(url: string, data: any): Promise<T> {
  return apiRequest<T>(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

/**
 * PATCH request helper
 */
export async function apiPatch<T>(url: string, data: any): Promise<T> {
  return apiRequest<T>(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

/**
 * DELETE request helper
 */
export async function apiDelete<T = void>(url: string): Promise<T> {
  const response = await apiFetch(url, { method: 'DELETE' });
  
  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }
  
  return response.json();
}

/**
 * Handle API errors with user-friendly messages
 */
export function handleApiError(error: unknown): string {
  if (error instanceof ApiException) {
    const apiError = error.error;
    
    // Rate limit error
    if (apiError?.code === 'RATE_LIMIT_EXCEEDED') {
      const retryAfter = apiError.retry_after;
      const tier = apiError.current_tier || 'FREE';
      
      let message = `Rate limit exceeded for ${tier} tier. `;
      
      if (retryAfter) {
        const minutes = Math.ceil(retryAfter / 60);
        message += `Please try again in ${minutes} minute${minutes > 1 ? 's' : ''}. `;
      }
      
      if (apiError.upgrade_available) {
        message += 'Upgrade your subscription for higher limits.';
      }
      
      return message;
    }
    
    // Tier restriction error
    if (apiError?.code === 'tier_restriction') {
      return apiError.message + ' Upgrade your subscription to access this feature.';
    }
    
    // Quota exceeded error
    if (apiError?.code === 'quota_exceeded') {
      return apiError.message;
    }
    
    // Generic API error
    return error.message;
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
}

/**
 * Check if error is due to tier restrictions
 */
export function isTierRestrictionError(error: unknown): boolean {
  if (error instanceof ApiException) {
    const code = error.error?.code;
    return code === 'tier_restriction' || code === 'PERMISSION_DENIED';
  }
  return false;
}

/**
 * Check if error is due to rate limiting
 */
export function isRateLimitError(error: unknown): boolean {
  if (error instanceof ApiException) {
    return error.error?.code === 'RATE_LIMIT_EXCEEDED';
  }
  return false;
}

/**
 * Extract retry-after time from error (in seconds)
 */
export function getRetryAfter(error: unknown): number | null {
  if (error instanceof ApiException) {
    return error.error?.retry_after || null;
  }
  return null;
}
