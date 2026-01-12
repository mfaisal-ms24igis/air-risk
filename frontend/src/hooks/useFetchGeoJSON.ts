/**
 * useFetchGeoJSON Hook
 * Generic hook for fetching GeoJSON data from any endpoint
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import apiClient from '@/api/client';
import type { GeoJSONFeatureCollection, GeoJSONGeometry, ApiError } from '@/types';

export interface UseFetchGeoJSONOptions {
  // If false, won't fetch until manually triggered
  enabled?: boolean;
  // Query parameters to append
  params?: Record<string, string | number | boolean | undefined>;
  // Refetch interval in ms (0 = disabled)
  refetchInterval?: number;
}

export interface UseFetchGeoJSONResult<P extends Record<string, unknown>> {
  data: GeoJSONFeatureCollection<GeoJSONGeometry, P> | null;
  isLoading: boolean;
  isError: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
}

export function useFetchGeoJSON<P extends Record<string, unknown> = Record<string, unknown>>(
  endpoint: string,
  options: UseFetchGeoJSONOptions = {}
): UseFetchGeoJSONResult<P> {
  const { enabled = true, params, refetchInterval = 0 } = options;

  const [data, setData] = useState<GeoJSONFeatureCollection<GeoJSONGeometry, P> | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  // Track if component is mounted to prevent state updates after unmount
  const isMountedRef = useRef<boolean>(true);
  // Track if fetch is in progress to prevent duplicate requests
  const fetchingRef = useRef<boolean>(false);
  // Store interval ID for cleanup
  const intervalRef = useRef<number | null>(null);
  // Track previous params to avoid unnecessary fetches
  const prevParamsRef = useRef<string>('');

  // Serialize params for stable comparison
  const paramsKey = useMemo(() => {
    if (!params) return '';
    const filtered = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined)
    );
    return JSON.stringify(filtered);
  }, [params]);

  const fetchData = useCallback(async () => {
    // Prevent duplicate requests
    if (fetchingRef.current) return;
    
    fetchingRef.current = true;
    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      // Filter out undefined params
      const filteredParams = params
        ? Object.fromEntries(
            Object.entries(params).filter(([, value]) => value !== undefined)
          )
        : undefined;

      const response = await apiClient.get<GeoJSONFeatureCollection<GeoJSONGeometry, P>>(
        endpoint,
        { params: filteredParams }
      ) as unknown as GeoJSONFeatureCollection<GeoJSONGeometry, P>;

      if (isMountedRef.current) {
        setData(response);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setIsError(true);
        setError(err as ApiError);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
      fetchingRef.current = false;
    }
  }, [endpoint, params]);

  // Initial fetch and refetch on dependency change
  useEffect(() => {
    isMountedRef.current = true;

    // Only fetch if params actually changed
    const shouldFetch = enabled && prevParamsRef.current !== paramsKey;
    
    if (shouldFetch) {
      prevParamsRef.current = paramsKey;
      fetchData();
    }

    return () => {
      isMountedRef.current = false;
    };
  }, [enabled, paramsKey, fetchData]);

  // Setup refetch interval
  useEffect(() => {
    if (refetchInterval > 0 && enabled) {
      intervalRef.current = window.setInterval(() => {
        fetchData();
      }, refetchInterval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [refetchInterval, enabled, fetchData]);

  return {
    data,
    isLoading,
    isError,
    error,
    refetch: fetchData,
  };
}

export default useFetchGeoJSON;
