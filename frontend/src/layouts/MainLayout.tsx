/**
 * MainLayout Component
 * 
 * Application shell layout with modern header and routing.
 * Wraps all pages and provides consistent structure.
 * 
 * @module layouts/MainLayout
 */

import { Outlet } from 'react-router-dom';
import { Header } from '@/components/layout/Header';

// =============================================================================
// Main Layout Component
// =============================================================================

export function MainLayout() {
  return (
    <div className="min-h-screen bg-space-navy-950">
      <Header />
      <main>
        <Outlet />
      </main>
    </div>
  );
}

export default MainLayout;
