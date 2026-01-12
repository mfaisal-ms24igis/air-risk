/**
 * Modern Map Page
 * 
 * Interactive geospatial map with air quality layers and district boundaries.
 * Uses MapLibre GL with GeoJSON from backend APIs.
 * @module pages/MapPage
 */

import { motion } from 'framer-motion';
import { UnifiedMap } from '@/features/map/components/UnifiedMap';

export default function MapPage() {
  return (
    <div className="fixed inset-0 w-full h-screen bg-space-navy-950 flex flex-col">
      {/* Header with title - minimal */}
      <div className="h-16 bg-space-navy-900/50 border-b border-white/10 flex items-center px-8 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-3"
        >
          <h1 className="text-xl font-bold text-foreground font-mono">Interactive Map</h1>
          <p className="text-xs text-muted-foreground hidden sm:block">Pakistan Air Quality Geospatial Dashboard</p>
        </motion.div>
      </div>

      {/* Main content - flex grow */}
      <div className="flex-1 flex overflow-hidden">
        {/* Map Area - takes full width */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="flex-1 w-full h-full relative overflow-hidden"
        >
          <div className="absolute inset-0">
            <UnifiedMap />
          </div>
          <div className="absolute bottom-4 left-4 text-xs text-muted-foreground bg-space-navy-900/80 px-3 py-2 rounded-lg backdrop-blur-md border border-white/10">
            <p className="flex items-center gap-2">
              <span>🖱️ Drag to pan • Scroll to zoom • Click features for details</span>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
