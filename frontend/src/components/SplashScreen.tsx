/**
 * Splash Screen Component
 * 
 * Full-screen intro animation with your custom Air RISK logo.
 * Displays for 3-5 seconds on app startup.
 * @module components/SplashScreen
 */

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AnimatedLogo } from './AnimatedLogo';

interface SplashScreenProps {
  /** Duration to show splash in milliseconds (default: 4000) */
  duration?: number;
  /** Callback when splash should be dismissed */
  onDismiss?: () => void;
}

export function SplashScreen({ duration = 4000, onDismiss }: SplashScreenProps) {
  const [show, setShow] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShow(false);
      onDismiss?.();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onDismiss]);

  // Background gradient animation
  const backgroundVariants = {
    animate: {
      background: [
        'linear-gradient(135deg, #0a192f 0%, #1a3a52 50%, #0ea5e9 100%)',
        'linear-gradient(135deg, #0a192f 0%, #0ea5e9 50%, #22c55e 100%)',
        'linear-gradient(135deg, #0a192f 0%, #1a3a52 50%, #0ea5e9 100%)',
      ],
      transition: {
        duration: duration / 1000,
        ease: 'easeInOut',
      },
    },
  };

  // Text fade-in animation
  const textVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        delay: 1.5,
        duration: 0.8,
      },
    },
    exit: {
      opacity: 0,
      transition: {
        duration: 0.5,
      },
    },
  };

  // Container fade-out animation
  const containerVariants = {
    visible: { opacity: 1 },
    exit: {
      opacity: 0,
      transition: { duration: 0.5 },
    },
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          variants={containerVariants}
          initial="visible"
          exit="exit"
          className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden"
        >
          {/* Animated Background */}
          <motion.div
            variants={backgroundVariants}
            animate="animate"
            className="absolute inset-0"
          />

          {/* Content */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="relative z-10 flex flex-col items-center gap-8"
          >
            {/* Logo with Intro Animation */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.8 }}
            >
              <AnimatedLogo showIntro size="lg" />
            </motion.div>

            {/* Tagline */}
            <motion.div
              variants={textVariants}
              initial="hidden"
              animate="visible"
              className="text-center"
            >
              <div className="flex items-baseline justify-center gap-2 mb-3">
                <h1 className="text-white text-4xl font-bold">Air</h1>
                <h1 className="text-transparent bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-4xl font-bold">RISK</h1>
              </div>
              <p className="text-gray-300 text-base font-medium mb-1">
                Real-time Intelligence
              </p>
              <p className="text-gray-300 text-base font-medium">
                Spatial Knowledge
              </p>
            </motion.div>

            {/* Loading Indicator */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.2, duration: 0.6 }}
              className="flex gap-1"
            >
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 bg-neon-green-400 rounded-full"
                  animate={{
                    scale: [1, 1.5, 1],
                    opacity: [0.5, 1, 0.5],
                  }}
                  transition={{
                    duration: 1.2,
                    delay: i * 0.2,
                    repeat: Infinity,
                  }}
                />
              ))}
            </motion.div>
          </motion.div>

          {/* Decorative elements */}
          <motion.div
            className="absolute top-20 left-10 w-32 h-32 bg-tech-blue-500 rounded-full mix-blend-multiply filter blur-2xl opacity-10"
            animate={{
              y: [0, 20, 0],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
          <motion.div
            className="absolute bottom-20 right-10 w-32 h-32 bg-neon-green-500 rounded-full mix-blend-multiply filter blur-2xl opacity-10"
            animate={{
              y: [0, -20, 0],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default SplashScreen;
