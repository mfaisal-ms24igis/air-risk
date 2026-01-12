/**
 * LoadingSpinner Component
 * 
 * A reusable loading indicator with multiple size variants.
 * 
 * @module components/ui/LoadingSpinner
 */

import './LoadingSpinner.css';

// =============================================================================
// Types
// =============================================================================

export interface LoadingSpinnerProps {
  /** Size variant */
  size?: 'small' | 'medium' | 'large';
  /** Optional label text */
  label?: string;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Animated loading spinner
 * 
 * @example
 * ```tsx
 * <LoadingSpinner size="large" label="Loading data..." />
 * ```
 */
export function LoadingSpinner({
  size = 'medium',
  label,
  className = '',
}: LoadingSpinnerProps) {
  return (
    <div className={`loading-spinner loading-spinner--${size} ${className}`}>
      <div className="spinner" role="status" aria-label={label || 'Loading'}>
        <div className="spinner-ring" />
      </div>
      {label && <span className="spinner-label">{label}</span>}
    </div>
  );
}

export default LoadingSpinner;
