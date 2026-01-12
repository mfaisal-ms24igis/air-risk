/**
 * useFetch Hook
 * Generic hook for fetching any data (non-GeoJSON)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/api/client';
import type { ApiError } from '@/types';

export interface UseFetchOptions {
  enabled?: boolean;
  params?: Record<string, string | number | boolean | undefined>;
  refetchInterval?: number;
}

export interface UseFetchResult<T> {
  data: T | null;
  isLoading: boolean;
  isError: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
}

export function useFetch<T>(
  endpoint: string,
  options: UseFetchOptions = {}
): UseFetchResult<T> {
  const { enabled = true, params, refetchInterval = 0 } = options;

  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  const isMountedRef = useRef<boolean>(true);
  const fetchingRef = useRef<boolean>(false);
  const intervalRef = useRef<number | null>(null);

  const fetchData = useCallback(async () => {
    if (fetchingRef.current) return;
    
    fetchingRef.current = true;
    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      const filteredParams = params
        ? Object.fromEntries(
            Object.entries(params).filter(([, value]) => value !== undefined)
          )
        : undefined;

      const response = await apiClient.get<T>(endpoint, { params: filteredParams });

      if (isMountedRef.current) {
        setData(response as T);
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

  useEffect(() => {
    isMountedRef.current = true;

    if (enabled) {
      fetchData();
    }

    return () => {
      isMountedRef.current = false;
    };
  }, [enabled, fetchData]);

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

export default useFetch;
