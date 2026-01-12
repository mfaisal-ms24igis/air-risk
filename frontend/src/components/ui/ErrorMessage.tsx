/**
 * ErrorMessage Component
 * 
 * Displays error messages with retry functionality.
 * 
 * @module components/ui/ErrorMessage
 */

import './ErrorMessage.css';

// =============================================================================
// Types
// =============================================================================

export interface ErrorMessageProps {
  /** Error title */
  title?: string;
  /** Error message to display */
  message: string;
  /** Retry callback */
  onRetry?: () => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Error message display with optional retry button
 * 
 * @example
 * ```tsx
 * <ErrorMessage 
 *   title="Failed to load"
 *   message={error.message}
 *   onRetry={() => refetch()}
 * />
 * ```
 */
export function ErrorMessage({
  title = 'Error',
  message,
  onRetry,
  className = '',
}: ErrorMessageProps) {
  return (
    <div className={`error-message ${className}`} role="alert">
      <div className="error-icon">⚠️</div>
      <div className="error-content">
        <h3 className="error-title">{title}</h3>
        <p className="error-text">{message}</p>
        {onRetry && (
          <button className="error-retry-btn" onClick={onRetry}>
            Try Again
          </button>
        )}
      </div>
    </div>
  );
}

export default ErrorMessage;
