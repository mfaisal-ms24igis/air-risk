/**
 * Axios API Client
 * Configured for Django REST Framework backend
 */

import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import type { ApiResponse, ApiError } from '@/types';

// Create axios instance with base configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 120000, // 120 seconds for GEE calculations
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Request interceptor - add auth token if available
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if stored (for future auth implementation)
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle standard response format
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Backend returns { status, data, message } - extract the data
    const responseData = response.data;
    
    // Check if it's our standard API format
    if (responseData && typeof responseData === 'object' && 'status' in responseData) {
      if (responseData.status === 'success') {
        // Return the actual data payload
        return responseData.data;
      } else {
        // Handle API-level errors
        return Promise.reject({
          status: 'error',
          message: responseData.message || 'An error occurred',
          errors: responseData.errors,
        } as ApiError);
      }
    }
    
    // For endpoints that return raw data (like GeoJSON directly)
    return response.data;
  },
  (error: AxiosError<ApiResponse<unknown>>) => {
    // Handle HTTP errors
    if (error.response) {
      const { status, data } = error.response;
      
      const apiError: ApiError = {
        status: 'error',
        message: (data as ApiResponse<unknown>)?.message || getDefaultErrorMessage(status),
        errors: (data as ApiResponse<unknown> & { errors?: Record<string, string[]> })?.errors,
        timestamp: new Date().toISOString(),
        statusCode: status,
      };
      
      return Promise.reject(apiError);
    }
    
    // Network error
    if (error.request) {
      return Promise.reject({
        status: 'error',
        message: 'Network error. Please check your connection.',
        timestamp: new Date().toISOString(),
      } as ApiError);
    }
    
    // Other errors
    return Promise.reject({
      status: 'error',
      message: error.message || 'An unexpected error occurred',
      timestamp: new Date().toISOString(),
    } as ApiError);
  }
);

// Helper function for default error messages
function getDefaultErrorMessage(status: number): string {
  const messages: Record<number, string> = {
    400: 'Bad request. Please check your input.',
    401: 'Unauthorized. Please log in.',
    403: 'Forbidden. You do not have permission.',
    404: 'Resource not found.',
    500: 'Server error. Please try again later.',
    502: 'Bad gateway. Server is temporarily unavailable.',
    503: 'Service unavailable. Please try again later.',
  };
  return messages[status] || 'An error occurred';
}

export default apiClient;
