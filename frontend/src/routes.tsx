/**
 * Application Routes Configuration
 * 
 * Centralized routing configuration using React Router v6.
 * Defines all application routes with lazy loading for code splitting.
 * 
 * @module routes
 */

import { lazy, Suspense } from 'react';
import type { RouteObject } from 'react-router-dom';
import { Navigate, Outlet } from 'react-router-dom';
import { MainLayout } from '@/layouts/MainLayout';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

// =============================================================================
// Lazy Loaded Pages
// =============================================================================

/**
 * Lazy load pages for code splitting
 * Each page is loaded only when navigated to
 */
const HomePage = lazy(() => import('@/pages/HomePage'));
const MapPage = lazy(() => import('@/pages/MapPageUpdated'));
const StationsPage = lazy(() => import('@/pages/StationsPage'));
const ReportsPage = lazy(() => import('@/pages/ReportsPageUpdated'));
const ExposureAnalysisPage = lazy(() => import('@/pages/ExposureAnalysisPage'));
const StationDetailPage = lazy(() =>
  Promise.resolve({
    default: () => (
      <div className="p-8">
        <h1>Station Details</h1>
        <p>Station detail page coming soon...</p>
        <a href="/stations">Back to Stations</a>
      </div>
    )
  })
);

const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'));
const ProfilePage = lazy(() => import('@/pages/ProfilePage'));
const UpgradePremiumPage = lazy(() => import('@/pages/UpgradePremiumPage'));

// =============================================================================
// Loading Fallback
// =============================================================================

/**
 * Suspense fallback component for lazy loaded pages
 */
function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
      <LoadingSpinner size="large" />
      <p>Loading...</p>
    </div>
  );
}

/**
 * Wrapper component that provides Suspense for lazy loaded routes
 */
function SuspenseLayout() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Outlet />
    </Suspense>
  );
}

// =============================================================================
// Route Definitions
// =============================================================================

/**
 * Route path constants for type-safe navigation
 */
export const ROUTES = {
  HOME: '/',
  MAP: '/map',
  STATIONS: '/stations',
  STATION_DETAIL: '/stations/:stationId',
  REPORTS: '/reports',
  EXPOSURE_ANALYSIS: '/exposure',
  LOGIN: '/login',
  REGISTER: '/register',
  PROFILE: '/profile',
  UPGRADE_PREMIUM: '/upgrade-premium',
} as const;

/**
 * Helper function to generate station detail path
 */
export function getStationDetailPath(stationId: number | string): string {
  return `/stations/${stationId}`;
}

/**
 * Route configuration array for useRoutes hook
 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        element: <SuspenseLayout />,
        children: [
          {
            index: true,
            element: <HomePage />,
          },
          {
            path: 'map',
            element: <MapPage />,
          },
          {
            path: 'stations',
            children: [
              {
                index: true,
                element: <StationsPage />,
              },
              {
                path: ':stationId',
                element: <StationDetailPage />,
              },
            ],
          },
          {
            path: 'reports',
            element: <ReportsPage />,
          },
          {
            path: 'exposure',
            element: <ExposureAnalysisPage />,
          },
          {
            path: 'profile',
            element: <ProfilePage />,
          },
          {
            path: 'upgrade-premium',
            element: (
              <Suspense fallback={<PageLoader />}>
                <UpgradePremiumPage />
              </Suspense>
            ),
          },
        ],
      },
    ],
  },
  {
    path: '/login',
    element: (
      <Suspense fallback={<PageLoader />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    path: '/register',
    element: (
      <Suspense fallback={<PageLoader />}>
        <RegisterPage />
      </Suspense>
    ),
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
];

export default routes;
