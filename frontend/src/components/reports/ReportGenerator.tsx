/**
 * ReportGenerator Component
 * 
 * Form for generating location-based air quality reports.
 * Handles both sync (BASIC) and async (PREMIUM) generation with polling.
 * 
 * @module components/reports/ReportGenerator
 */

import { useState } from 'react';
import { useAuthStore, useReportStore, useIsPremium, useTier, useGenerationState } from '@/store';
import type { CreateLocationReportRequest } from '@/types/reports';

// =============================================================================
// Constants
// =============================================================================

const PAKISTAN_BOUNDS = {
  minLat: 23.69,
  maxLat: 37.08,
  minLng: 60.87,
  maxLng: 77.84,
};

const MAX_RADIUS_KM = 50;
const MAX_DATE_RANGE_DAYS = 30;

// =============================================================================
// Component
// =============================================================================

export function ReportGenerator() {
  const { accessToken } = useAuthStore();
  const { createLocationReport, clearError } = useReportStore();
  const generationState = useGenerationState();
  const isPremium = useIsPremium();
  const tier = useTier();

  // Form state
  const [formData, setFormData] = useState<CreateLocationReportRequest>({
    lat: 31.5204, // Lahore
    lng: 74.3587,
    radius_km: 5.0,
    start_date: getDefaultStartDate(),
    end_date: getDefaultEndDate(),
    include_ai: false,
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // =============================================================================
  // Helpers
  // =============================================================================

  function getDefaultEndDate(): string {
    const today = new Date();
    return today.toISOString().split('T')[0];
  }

  function getDefaultStartDate(): string {
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    return thirtyDaysAgo.toISOString().split('T')[0];
  }

  // =============================================================================
  // Validation
  // =============================================================================

  function validateForm(): boolean {
    const errors: Record<string, string> = {};

    // Validate coordinates
    if (formData.lat < PAKISTAN_BOUNDS.minLat || formData.lat > PAKISTAN_BOUNDS.maxLat) {
      errors.lat = `Latitude must be between ${PAKISTAN_BOUNDS.minLat} and ${PAKISTAN_BOUNDS.maxLat}`;
    }

    if (formData.lng < PAKISTAN_BOUNDS.minLng || formData.lng > PAKISTAN_BOUNDS.maxLng) {
      errors.lng = `Longitude must be between ${PAKISTAN_BOUNDS.minLng} and ${PAKISTAN_BOUNDS.maxLng}`;
    }

    // Validate radius
    if (formData.radius_km <= 0 || formData.radius_km > MAX_RADIUS_KM) {
      errors.radius_km = `Radius must be between 1 and ${MAX_RADIUS_KM} km`;
    }

    // Validate date range
    const startDate = new Date(formData.start_date);
    const endDate = new Date(formData.end_date);
    const daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));

    if (daysDiff <= 0) {
      errors.date_range = 'End date must be after start date';
    } else if (daysDiff > MAX_DATE_RANGE_DAYS) {
      errors.date_range = `Date range cannot exceed ${MAX_DATE_RANGE_DAYS} days`;
    }

    // Validate AI option
    if (formData.include_ai && !isPremium) {
      errors.include_ai = 'AI insights require a premium subscription';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }

  // =============================================================================
  // Handlers
  // =============================================================================

  function handleInputChange(field: keyof CreateLocationReportRequest, value: any) {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
    
    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors((prev) => {
        const { [field]: _, ...rest } = prev;
        return rest;
      });
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!accessToken) {
      alert('Please log in to generate reports');
      return;
    }

    if (!validateForm()) {
      return;
    }

    try {
      await createLocationReport(formData, accessToken);
    } catch (error) {
      console.error('Failed to create report:', error);
    }
  }

  function handleUseCurrentLocation() {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setFormData((prev) => ({
            ...prev,
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          }));
        },
        (error) => {
          alert('Failed to get current location: ' + error.message);
        }
      );
    } else {
      alert('Geolocation is not supported by your browser');
    }
  }

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Generate Location Report</h2>
        <p className="mt-2 text-sm text-gray-600">
          Get a comprehensive air quality analysis for any location in Pakistan
        </p>
        
        {/* Tier badge */}
        <div className="mt-3 inline-flex items-center gap-2">
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold ${
              isPremium
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}
          >
            {tier}
          </span>
          {isPremium && (
            <span className="text-xs text-gray-600">
              ✨ AI insights enabled
            </span>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Location */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Latitude
            </label>
            <input
              type="number"
              step="0.0001"
              value={formData.lat}
              onChange={(e) => handleInputChange('lat', parseFloat(e.target.value))}
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 ${
                validationErrors.lat ? 'border-red-500' : 'border-gray-300'
              }`}
              title="Enter latitude (decimal degrees)"
              required
            />
            {validationErrors.lat && (
              <p className="mt-1 text-xs text-red-600">{validationErrors.lat}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Longitude
            </label>
            <input
              type="number"
              step="0.0001"
              value={formData.lng}
              onChange={(e) => handleInputChange('lng', parseFloat(e.target.value))}
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 ${
                validationErrors.lng ? 'border-red-500' : 'border-gray-300'
              }`}
              title="Enter longitude (decimal degrees)"
              required
            />
            {validationErrors.lng && (
              <p className="mt-1 text-xs text-red-600">{validationErrors.lng}</p>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={handleUseCurrentLocation}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          📍 Use my current location
        </button>

        {/* Radius */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Search Radius (km)
          </label>
          <input
            type="number"
            step="0.5"
            min="1"
            max={MAX_RADIUS_KM}
            value={formData.radius_km}
            onChange={(e) => handleInputChange('radius_km', parseFloat(e.target.value))}
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 ${
              validationErrors.radius_km ? 'border-red-500' : 'border-gray-300'
            }`}
            title="Enter search radius in kilometers"
            required
          />
          {validationErrors.radius_km && (
            <p className="mt-1 text-xs text-red-600">{validationErrors.radius_km}</p>
          )}
          <p className="mt-1 text-xs text-gray-600">
            Max {MAX_RADIUS_KM} km • {isPremium ? 'Up to 50 stations' : 'Up to 10 stations'}
          </p>
        </div>

        {/* Date Range */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={formData.start_date}
              onChange={(e) => handleInputChange('start_date', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              title="Select start date for analysis"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={formData.end_date}
              onChange={(e) => handleInputChange('end_date', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              title="Select end date for analysis"
              required
            />
          </div>
        </div>

        {validationErrors.date_range && (
          <p className="text-xs text-red-600">{validationErrors.date_range}</p>
        )}

        <p className="text-xs text-gray-600">
          Maximum {MAX_DATE_RANGE_DAYS} day range
        </p>

        {/* AI Insights (Premium only) */}
        <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-md">
          <input
            type="checkbox"
            id="include_ai"
            checked={formData.include_ai}
            onChange={(e) => handleInputChange('include_ai', e.target.checked)}
            disabled={!isPremium}
            className="mt-1"
          />
          <label htmlFor="include_ai" className="flex-1">
            <span className="text-sm font-medium text-gray-900">
              Include AI Health Recommendations
            </span>
            <p className="mt-1 text-xs text-gray-600">
              Get personalized health advice based on pollutant levels (Premium only)
            </p>
            {!isPremium && (
              <p className="mt-2 text-xs text-blue-600 font-medium">
                Upgrade to Premium to unlock AI insights
              </p>
            )}
          </label>
        </div>

        {validationErrors.include_ai && (
          <p className="text-xs text-red-600">{validationErrors.include_ai}</p>
        )}

        {/* Error display */}
        {generationState.error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-800">{generationState.error}</p>
            <button
              type="button"
              onClick={clearError}
              className="mt-2 text-xs text-red-600 hover:text-red-700 font-medium"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Progress bar */}
        {generationState.isGenerating && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-700">Generating report...</span>
              <span className="text-gray-600">{generationState.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${generationState.progress}%` }}
              />
            </div>
            {generationState.estimatedTimeRemaining > 0 && (
              <p className="text-xs text-gray-600">
                Estimated time: {generationState.estimatedTimeRemaining}s
              </p>
            )}
          </div>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={generationState.isGenerating}
          className={`w-full px-6 py-3 rounded-md font-semibold text-white transition-colors ${
            generationState.isGenerating
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {generationState.isGenerating ? 'Generating...' : 'Generate Report'}
        </button>

        {/* Tier info */}
        <div className="text-xs text-gray-600 space-y-1">
          <p>
            <strong>{tier} tier:</strong>{' '}
            {isPremium
              ? 'Async generation with AI insights, 30-day storage'
              : 'Instant generation, 7-day storage'}
          </p>
        </div>
      </form>
    </div>
  );
}

export default ReportGenerator;
