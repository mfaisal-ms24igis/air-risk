/**
 * Splash Screen Management Hook
 * 
 * Manages splash screen state and visibility.
 * Shows splash on first app load or after certain events.
 * @module hooks/useSplashScreen
 */

import { create } from 'zustand';

interface SplashScreenState {
  showSplash: boolean;
  setShowSplash: (show: boolean) => void;
  dismissSplash: () => void;
  resetSplash: () => void;
}

/**
 * Zustand store for splash screen state
 */
export const useSplashScreenStore = create<SplashScreenState>((set) => ({
  showSplash: true,
  setShowSplash: (show) => set({ showSplash: show }),
  dismissSplash: () => set({ showSplash: false }),
  resetSplash: () => set({ showSplash: true }),
}));

/**
 * Hook for managing splash screen
 * 
 * @example
 * const { showSplash, dismissSplash } = useSplashScreen();
 * 
 * if (showSplash) {
 *   return <SplashScreen onDismiss={dismissSplash} />;
 * }
 */
export const useSplashScreen = () => {
  const { showSplash, dismissSplash, resetSplash } = useSplashScreenStore();

  return {
    showSplash,
    dismissSplash,
    resetSplash,
  };
};
