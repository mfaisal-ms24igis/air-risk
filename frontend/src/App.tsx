/**
 * App Component
 * 
 * Root application component that renders the router.
 * Uses React Router for multi-page navigation.
 * Displays animated splash screen on app startup.
 */

import { useRoutes } from 'react-router-dom';

import { routes } from '@/routes';
import { AuthProvider } from '@/contexts/AuthContext';
import { ToastProvider } from '@/contexts/ToastContext';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { SplashScreen } from '@/components/SplashScreen';
import { useSplashScreen } from '@/hooks/useSplashScreen';
import './App.css';

function AppContent() {
  const { showSplash, dismissSplash } = useSplashScreen();

  // Render routes from centralized configuration
  const routeElement = useRoutes(routes);

  return (
    <>
      {showSplash && <SplashScreen onDismiss={dismissSplash} duration={4000} />}
      {routeElement}
    </>
  );
}

function App() {
  return (
    <ErrorBoundary showDetails={import.meta.env.DEV}>
      <AuthProvider>
        <ToastProvider position="top-right" maxToasts={5}>
          <AppContent />
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
