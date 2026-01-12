/**
 * Card Component
 * 
 * Reusable card container with variants.
 * 
 * @module components/ui/Card
 */

import type { ReactNode, HTMLAttributes } from 'react';
import './Card.css';

// =============================================================================
// Types
// =============================================================================

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Card content */
  children: ReactNode;
  /** Card variant */
  variant?: 'default' | 'outlined' | 'elevated';
  /** Optional padding override */
  padding?: 'none' | 'small' | 'medium' | 'large';
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Card container component
 */
export function Card({
  children,
  variant = 'default',
  padding = 'medium',
  className = '',
  ...props
}: CardProps) {
  return (
    <div
      className={`card card--${variant} card--padding-${padding} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Card Header component
 */
export function CardHeader({
  children,
  className = '',
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`card-header ${className}`} {...props}>
      {children}
    </div>
  );
}

/**
 * Card Title component
 */
export function CardTitle({
  children,
  className = '',
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={`card-title ${className}`} {...props}>
      {children}
    </h3>
  );
}

/**
 * Card Content component
 */
export function CardContent({
  children,
  className = '',
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`card-content ${className}`} {...props}>
      {children}
    </div>
  );
}

/**
 * Card Footer component
 */
export function CardFooter({
  children,
  className = '',
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`card-footer ${className}`} {...props}>
      {children}
    </div>
  );
}

export default Card;
