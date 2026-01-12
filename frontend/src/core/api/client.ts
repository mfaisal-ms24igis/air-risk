/**
 * Enterprise API Client
 * 
 * Centralized API client with interceptors, retry logic, and error handling
 * Provides consistent interface for all API calls
 * 
 * @module core/api/client
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

// =============================================================================
// Configuration
// =============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const API_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

// =============================================================================
// Types
// =============================================================================

export interface APIError {
  message: string;
  statusCode?: number;
  errors?: Record<string, string[]>;
  detail?: string;
}

export interface APIResponse<T = any> {
  data: T;
  message?: string;
  status: string;
}

export interface PaginatedResponse<T = any> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// =============================================================================
// API Client Class
// =============================================================================

class APIClient {
  private client: AxiosInstance;
  private retryCount: Map<string, number> = new Map();

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  /**
   * Setup request and response interceptors
   */
  private setupInterceptors(): void {
    // Request Interceptor
    this.client.interceptors.request.use(
      this.handleRequest.bind(this),
      this.handleRequestError.bind(this)
    );

    // Response Interceptor
    this.client.interceptors.response.use(
      this.handleResponse.bind(this),
      this.handleResponseError.bind(this)
    );
  }

  /**
   * Request interceptor - Add auth token
   */
  private handleRequest(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
    // Add authentication token
    const token = this.getAuthToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Add request timestamp for logging
    (config as any).metadata = { startTime: Date.now() };

    return config;
  }

  /**
   * Request error interceptor
   */
  private handleRequestError(error: any): Promise<never> {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }

  /**
   * Response interceptor - Handle success
   */
  private handleResponse(response: AxiosResponse): AxiosResponse {
    // Log response time in development
    if (import.meta.env.DEV) {
      const startTime = (response.config as any).metadata?.startTime;
      if (startTime) {
        const duration = Date.now() - startTime;
        console.log(`API Call: ${response.config.url} - ${duration}ms`);
      }
    }

    return response;
  }

  /**
   * Response error interceptor - Handle errors with retry logic
   */
  private async handleResponseError(error: AxiosError): Promise<any> {
    const config = error.config as AxiosRequestConfig & { _retry?: boolean; _retryCount?: number };

    // Handle network errors
    if (!error.response) {
      console.error('Network Error:', error.message);
      return Promise.reject(this.formatError(error));
    }

    const { status } = error.response;

    // Handle 401 Unauthorized - Try to refresh token
    if (status === 401 && !config._retry) {
      config._retry = true;

      try {
        await this.refreshAuthToken();
        return this.client.request(config);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        this.handleAuthenticationFailure();
        return Promise.reject(this.formatError(error));
      }
    }

    // Handle 429 Too Many Requests - Don't retry to prevent infinite loops
    if (status === 429) {
      console.error('Rate limit exceeded (429). Please wait before retrying.');
      return Promise.reject(this.formatError(error));
    }

    // Handle 5xx Server Errors - Retry with exponential backoff
    if (status >= 500 && status < 600) {
      const retryCount = config._retryCount || 0;

      if (retryCount < MAX_RETRIES) {
        config._retryCount = retryCount + 1;
        const delay = RETRY_DELAY * Math.pow(2, retryCount);

        console.log(`Retrying request (${retryCount + 1}/${MAX_RETRIES}) after ${delay}ms`);
        await this.sleep(delay);
        return this.client.request(config);
      }
    }

    return Promise.reject(this.formatError(error));
  }

  /**
   * Format error for consistent error handling
   */
  private formatError(error: AxiosError): APIError {
    const response = error.response?.data as any;

    return {
      message: response?.message || response?.detail || error.message || 'An unexpected error occurred',
      statusCode: error.response?.status,
      errors: response?.errors,
      detail: response?.detail,
    };
  }

  /**
   * Get authentication token from storage
   */
  private getAuthToken(): string | null {
    return localStorage.getItem('access_token');
  }

  /**
   * Refresh authentication token
   */
  private async refreshAuthToken(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
        refresh: refreshToken,
      });

      const { access } = response.data;
      localStorage.setItem('access_token', access);
    } catch (error) {
      // Clear tokens on refresh failure
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      throw error;
    }
  }

  /**
   * Handle authentication failure - redirect to login
   */
  private handleAuthenticationFailure(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    // Redirect to login if not already there
    if (window.location.pathname !== '/login') {
      window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
    }
  }

  /**
   * Sleep utility for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ========================================================================
  // Public API Methods
  // ========================================================================

  /**
   * GET request
   */
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  /**
   * POST request
   */
  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  /**
   * PUT request
   */
  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  /**
   * PATCH request
   */
  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  /**
   * DELETE request
   */
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  /**
   * Upload file
   */
  async upload<T = any>(url: string, formData: FormData, onProgress?: (progress: number) => void): Promise<T> {
    const response = await this.client.post<T>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  }

  /**
   * Download file
   */
  async download(url: string, filename?: string): Promise<void> {
    const response = await this.client.get(url, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.download = filename || 'download';
    link.click();
    window.URL.revokeObjectURL(link.href);
  }

  /**
   * Get raw axios instance for advanced use cases
   */
  getAxiosInstance(): AxiosInstance {
    return this.client;
  }
}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const apiClient = new APIClient();
export default apiClient;
