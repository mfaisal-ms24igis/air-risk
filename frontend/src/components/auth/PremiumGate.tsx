import { ReactNode } from 'react';
import { useUserTier } from '@/hooks/useUserTier';
import { Lock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PremiumGateProps {
  children: ReactNode;
  fallback?: ReactNode;
  showUpgradeMessage?: boolean;
  className?: string;
}

/**
 * Component that restricts content to PREMIUM users only
 * Shows upgrade message for BASIC users by default
 */
export function PremiumGate({
  children,
  fallback,
  showUpgradeMessage = true,
  className,
}: PremiumGateProps) {
  const { isPremium } = useUserTier();

  if (isPremium) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  if (showUpgradeMessage) {
    return (
      <div className={cn(
        'flex flex-col items-center justify-center p-8 bg-muted/50 rounded-lg border-2 border-dashed border-border',
        className
      )}>
        <div className="flex items-center gap-2 text-muted-foreground mb-2">
          <Lock className="h-5 w-5" />
          <span className="font-semibold">Premium Feature</span>
        </div>
        <p className="text-sm text-center text-muted-foreground max-w-sm">
          Upgrade to Premium to access this feature and unlock advanced analytics,
          custom reports, and detailed district insights.
        </p>
      </div>
    );
  }

  return null;
}
