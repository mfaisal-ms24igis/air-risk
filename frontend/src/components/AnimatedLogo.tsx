/**
 * Animated Logo Component
 * 
 * Uses Air RISK geospatial icon with animations.
 * Features rotation and pulsing effects for loading states.
 * @module components/AnimatedLogo
 */

import { motion } from 'framer-motion';

interface AnimatedLogoProps {
  /** Show intro animation sequence */
  showIntro?: boolean;
  /** Show as loading spinner */
  isLoading?: boolean;
  /** Logo size: sm, md, lg */
  size?: 'sm' | 'md' | 'lg';
  /** Custom className */
  className?: string;
}

const sizeConfig = {
  sm: { size: 32, scale: 0.8 },
  md: { size: 64, scale: 1 },
  lg: { size: 96, scale: 1.2 },
};

export function AnimatedLogo({
  showIntro = false,
  isLoading = false,
  size = 'md',
  className = '',
}: AnimatedLogoProps) {
  const config = sizeConfig[size];

  // Intro animation sequence
  const introVariants = {
    hidden: { opacity: 0, scale: 0 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: {
        duration: 0.6,
      },
    },
  };

  // Logo rotation animation for loading
  const rotationVariants = {
    animate: {
      rotate: 360,
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: 'linear' as const,
      },
    },
  };

  // Pulsing glow effect
  const glowVariants = {
    animate: {
      opacity: [0.5, 1, 0.5],
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut' as const,
      },
    },
  };

  return (
    <motion.div
      className={`flex items-center justify-center ${className}`}
      initial={showIntro ? 'hidden' : 'visible'}
      animate="visible"
      variants={introVariants}
    >
      {/* Logo Container */}
      <div className="relative">
        {/* Glow effect for loading */}
        {isLoading && (
          <motion.div
            className="absolute inset-0 bg-tech-blue-500/30 rounded-full blur-xl"
            variants={glowVariants}
            animate="animate"
          />
        )}

        {/* Logo Image */}
        <motion.img
          src="/Air_RISK_logo_onlyicon_removedbg.png"
          alt="AIR RISK Geospatial Icon"
          width={config.size}
          height={config.size}
          className="drop-shadow-lg object-contain"
          animate={isLoading ? 'animate' : 'initial'}
          variants={rotationVariants}
          style={{ transformOrigin: 'center' }}
        />
      </div>
    </motion.div>
  );
}

export default AnimatedLogo;
