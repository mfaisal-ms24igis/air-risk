/**
 * useStationTimeSeries Hook
 * 
 * Fetches historical air quality data for a specific station from the backend.
 * Used for populating charts in the Station Detail Panel.
 * 
 * @module hooks/queries/useStationTimeSeries
 */

import { useQuery } from '@tanstack/react-query';
import api from '@/lib/axios';
import { TimeSeriesPoint, PollutantCode } from '@/types/models';

// =============================================================================
// Types
// =============================================================================

export interface TimeSeriesResponse {
    station_id: number;
    param: string;
    period: string;
    data: TimeSeriesPoint[];
}

export interface UseStationTimeSeriesParams {
    stationId?: number | string;
    days?: number;
    pollutant?: PollutantCode;
}

// =============================================================================
// Query Key Factory
// =============================================================================

export const stationKeys = {
    all: ['stations'] as const,
    timeSeries: (stationId: number | string, days: number, pollutant: string) =>
        [...stationKeys.all, 'timeSeries', stationId, days, pollutant] as const,
};

// =============================================================================
// Hook Definition
// =============================================================================

export function useStationTimeSeries({ stationId, days = 7, pollutant = 'PM25' }: UseStationTimeSeriesParams) {
    return useQuery({
        queryKey: stationKeys.timeSeries(stationId || '', days, pollutant),
        queryFn: async () => {
            if (!stationId) throw new Error('Station ID is required');

            const response = await api.get<TimeSeriesResponse>(
                `/stations/${stationId}/timeseries/`,
                { params: { days, parameter: pollutant } }  // Backend expects 'parameter' not 'pollutant'
            );

            return response;
        },
        enabled: !!stationId,
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}
