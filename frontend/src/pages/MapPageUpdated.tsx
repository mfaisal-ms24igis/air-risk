/**
 * Modern Minimal Map Page
 * 
 * Clean, professional air quality map interface with minimal UI clutter.
 * Focus on the data visualization with subtle, elegant controls.
 * 
 * @module pages/MapPageUpdated
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UnifiedMap } from '@/features/map/components/UnifiedMap';
import { useAuth } from '@/contexts/AuthContext';
import { useUserTier } from '@/hooks/useUserTier';
import { Crown } from 'lucide-react';

export default function MapPageUpdated() {
  const { user } = useAuth();
  const { tier, isPremium } = useUserTier();
  const [showPremiumFeatures, setShowPremiumFeatures] = useState(isPremium);

  return (
    <div className="fixed inset-0 w-full h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Minimalist floating header */}
      <motion.div
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 100, damping: 20 }}
        className="absolute top-6 left-6 right-6 z-[900] flex items-center justify-between pointer-events-none"
      >
        <div className="pointer-events-auto flex-1 flex items-center justify-between">
          {/* Title */}
          <motion.div
            className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl px-6 py-3 shadow-2xl"
            whileHover={{ scale: 1.02 }}
          >
            <h1 className="text-lg font-semibold text-white tracking-tight">
              Air Quality Map
            </h1>
          </motion.div>

          {/* Tier indicator - minimal */}
          <motion.div
            className={`backdrop-blur-xl rounded-2xl px-5 py-3 shadow-2xl border ${isPremium
                ? 'bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border-amber-400/30'
                : 'bg-white/5 border-white/10'
              }`}
            whileHover={{ scale: 1.05 }}
          >
            <div className="flex items-center gap-2">
              {isPremium && <Crown className="w-4 h-4 text-amber-400" />}
              <span className={`text-sm font-medium ${isPremium ? 'text-amber-300' : 'text-gray-300'}`}>
                {isPremium ? 'Premium' : 'Basic'}
              </span>
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* Full-screen map */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
        className="absolute inset-0"
      >
        <UnifiedMap enablePremiumFeatures={showPremiumFeatures} />
      </motion.div>

      {/* Subtle upgrade prompt for basic users - bottom right */}
      <AnimatePresence>
        {!isPremium && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 100, damping: 20, delay: 1 }}
            className="absolute bottom-6 right-6 z-20"
          >
            <motion.button
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => window.location.href = '/upgrade'}
              className="group bg-gradient-to-r from-amber-500 to-yellow-500 text-white rounded-2xl px-6 py-4 shadow-2xl border border-amber-400/30 hover:shadow-amber-500/20 transition-all"
            >
              <div className="flex items-center gap-3">
                <Crown className="w-5 h-5" />
                <div className="text-left">
                  <p className="text-sm font-bold leading-tight">Unlock Premium</p>
                  <p className="text-xs text-amber-50/80">Satellite • Analytics • More</p>
                </div>
              </div>
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
