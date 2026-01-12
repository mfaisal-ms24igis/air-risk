import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Get AQI level from value (EPA Standard)
 */
export function getAqiLevel(aqi: number): {
  level: 'good' | 'moderate' | 'usg' | 'unhealthy' | 'veryUnhealthy' | 'hazardous';
  label: string;
  color: string;
} {
  if (aqi <= 50) {
    return { level: 'good', label: 'Good', color: '#00E400' };
  } else if (aqi <= 100) {
    return { level: 'moderate', label: 'Moderate', color: '#FFFF00' };
  } else if (aqi <= 150) {
    return { level: 'usg', label: 'Unhealthy for Sensitive Groups', color: '#FF7E00' };
  } else if (aqi <= 200) {
    return { level: 'unhealthy', label: 'Unhealthy', color: '#FF0000' };
  } else if (aqi <= 300) {
    return { level: 'veryUnhealthy', label: 'Very Unhealthy', color: '#8F3F97' };
  } else {
    return { level: 'hazardous', label: 'Hazardous', color: '#7E0023' };
  }
}

/**
 * Format date for API requests
 */
export function formatDateForApi(date: Date): string {
  return date.toISOString().split('T')[0];
}

/**
 * Calculate days between two dates
 */
export function daysBetween(start: Date, end: Date): number {
  const diff = Math.abs(end.getTime() - start.getTime());
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}
