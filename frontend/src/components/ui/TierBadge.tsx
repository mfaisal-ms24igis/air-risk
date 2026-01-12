/**
 * Tier Badge Component
 * 
 * Displays user subscription tier (BASIC/PREMIUM) with styling
 * 
 * @module components/ui/TierBadge
 */

import { Crown, User } from 'lucide-react';
import { motion } from 'framer-motion';

export interface TierBadgeProps {
  tier: 'BASIC' | 'PREMIUM';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showLabel?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-1.5 text-base',
};

const iconSizes = {
  sm: 12,
  md: 14,
  lg: 16,
};

export function TierBadge({
  tier,
  size = 'md',
  showIcon = true,
  showLabel = true,
  className = '',
}: TierBadgeProps) {
  const isBasic = tier === 'BASIC';
  const Icon = isBasic ? User : Crown;

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={`
        inline-flex items-center gap-1.5 font-semibold rounded-full
        ${isBasic 
          ? 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' 
          : 'bg-gradient-to-r from-yellow-400 to-amber-500 text-white shadow-lg shadow-yellow-500/30'
        }
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {showIcon && (
        <Icon 
          size={iconSizes[size]} 
          className={isBasic ? '' : 'animate-pulse'}
        />
      )}
      {showLabel && <span>{tier}</span>}
    </motion.div>
  );
}

/**
 * Upgrade Prompt Component
 * Shows when user tries to access premium features
 */
export interface UpgradePromptProps {
  feature: string;
  onUpgrade?: () => void;
}

export function UpgradePrompt({ feature, onUpgrade }: UpgradePromptProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/20 dark:to-amber-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <Crown className="w-6 h-6 text-amber-500" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
            Premium Feature
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {feature} is available for Premium users only. Upgrade to unlock this and other advanced features.
          </p>
          {onUpgrade && (
            <button
              onClick={onUpgrade}
              className="mt-3 px-4 py-2 bg-gradient-to-r from-yellow-400 to-amber-500 text-white text-sm font-medium rounded-lg hover:from-yellow-500 hover:to-amber-600 transition-all shadow-md hover:shadow-lg"
            >
              Upgrade to Premium
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default TierBadge;
