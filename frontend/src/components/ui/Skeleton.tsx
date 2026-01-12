/**
 * Skeleton Loaders
 * 
 * Professional loading placeholders for better perceived performance
 * Creates smooth, animated loading states
 * 
 * @module components/ui/Skeleton
 */

import { motion } from 'framer-motion';
import { HTMLAttributes } from 'react';

// =============================================================================
// Base Skeleton Component
// =============================================================================

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export function Skeleton({ 
  className = '', 
  variant = 'rectangular',
  width,
  height,
  animation = 'pulse',
  style,
  ...props 
}: SkeletonProps) {
  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-md',
  };

  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'animate-shimmer bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%]',
    none: '',
  };

  return (
    <div
      className={`bg-gray-200 ${variantClasses[variant]} ${animationClasses[animation]} ${className}`}
      style={{
        width,
        height,
        ...style,
      }}
      {...props}
    />
  );
}

// =============================================================================
// Preset Skeleton Components
// =============================================================================

/**
 * Card Skeleton - For card components
 */
export function CardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
      <Skeleton height={24} width="60%" />
      <Skeleton height={16} width="100%" />
      <Skeleton height={16} width="90%" />
      <Skeleton height={16} width="95%" />
      <div className="flex gap-4 pt-4">
        <Skeleton height={40} width={100} />
        <Skeleton height={40} width={100} />
      </div>
    </div>
  );
}

/**
 * Table Skeleton - For table components
 */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 border-b border-gray-200 p-4">
        <div className="flex gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} height={20} width="20%" />
          ))}
        </div>
      </div>
      
      {/* Rows */}
      <div className="divide-y divide-gray-200">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="p-4">
            <div className="flex gap-4">
              {[1, 2, 3, 4].map((j) => (
                <Skeleton key={j} height={16} width="20%" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * List Skeleton - For list components
 */
export function ListSkeleton({ items = 5 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-4 bg-white rounded-lg shadow">
          <Skeleton variant="circular" width={48} height={48} />
          <div className="flex-1 space-y-2">
            <Skeleton height={20} width="40%" />
            <Skeleton height={16} width="60%" />
          </div>
          <Skeleton height={32} width={80} />
        </div>
      ))}
    </div>
  );
}

/**
 * Profile Skeleton - For user profile
 */
export function ProfileSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center gap-6">
        <Skeleton variant="circular" width={96} height={96} />
        <div className="flex-1 space-y-3">
          <Skeleton height={28} width="50%" />
          <Skeleton height={20} width="70%" />
          <Skeleton height={20} width="40%" />
        </div>
      </div>
      <div className="mt-6 grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="text-center space-y-2">
            <Skeleton height={36} width="100%" />
            <Skeleton height={16} width="80%" className="mx-auto" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Map Skeleton - For map components
 */
export function MapSkeleton() {
  return (
    <div className="relative w-full h-full min-h-[400px] bg-gray-100 rounded-lg overflow-hidden">
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto"></div>
          <p className="text-gray-500 font-medium">Loading map...</p>
        </div>
      </div>
      
      {/* Decorative elements */}
      <div className="absolute top-4 left-4">
        <Skeleton height={120} width={200} className="bg-white/50" />
      </div>
      <div className="absolute top-4 right-4 space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} height={40} width={40} className="bg-white/50" />
        ))}
      </div>
    </div>
  );
}

/**
 * Chart Skeleton - For chart components
 */
export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="space-y-4">
        <Skeleton height={24} width="40%" />
        <Skeleton height={height} width="100%" />
        <div className="flex justify-center gap-6 pt-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton variant="circular" width={12} height={12} />
              <Skeleton height={16} width={60} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Dashboard Skeleton - Full dashboard loading state
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <Skeleton height={32} width={200} />
        <Skeleton height={40} width={120} />
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow-md p-6 space-y-2">
            <Skeleton height={16} width="50%" />
            <Skeleton height={36} width="70%" />
            <Skeleton height={12} width="40%" />
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ChartSkeleton height={400} />
        </div>
        <div>
          <ListSkeleton items={6} />
        </div>
      </div>
    </div>
  );
}

/**
 * Page Skeleton - Generic page loading
 */
export function PageSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <Skeleton height={40} width={300} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <div>
            <CardSkeleton />
          </div>
        </div>
      </div>
    </div>
  );
}
