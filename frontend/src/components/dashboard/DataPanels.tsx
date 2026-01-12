import { ReactNode } from 'react';
import { Activity, Users, Wind, TrendingUp, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  trend?: number;
  icon?: ReactNode;
  status?: 'good' | 'warning' | 'danger';
  subtitle?: string;
  isLive?: boolean;
  className?: string;
}

export function MetricCard({
  title,
  value,
  unit,
  trend,
  icon,
  status = 'good',
  subtitle,
  isLive = false,
  className,
}: MetricCardProps) {
  const statusColors = {
    good: 'text-neon-green-400 border-neon-green-500/30',
    warning: 'text-yellow-400 border-yellow-500/30',
    danger: 'text-red-400 border-red-500/30',
  };

  const glowColors = {
    good: 'shadow-[0_0_20px_rgba(34,197,94,0.3)]',
    warning: 'shadow-[0_0_20px_rgba(250,204,21,0.3)]',
    danger: 'shadow-[0_0_20px_rgba(239,68,68,0.3)]',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={cn(
        'metric-card relative group',
        statusColors[status],
        className
      )}
    >
      {/* Scan line animation */}
      <div className="scan-line opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          {icon && (
            <div className={cn('p-2 rounded-lg bg-white/5', statusColors[status])}>
              {icon}
            </div>
          )}
          <div>
            <h4 className="text-xs font-mono uppercase tracking-wider text-gray-400">
              {title}
            </h4>
            {subtitle && (
              <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
        {isLive && (
          <div className="flex items-center gap-1.5 text-xs text-neon-green-400">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-neon-green-500"></span>
            </span>
            LIVE
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-2">
        <span className={cn(
          'text-4xl font-bold font-mono tracking-tight',
          statusColors[status],
          glowColors[status]
        )}>
          {value}
        </span>
        {unit && (
          <span className="text-lg text-gray-400 font-mono">{unit}</span>
        )}
      </div>

      {/* Trend indicator */}
      {trend !== undefined && (
        <div className={cn(
          'flex items-center gap-1 mt-3 text-sm font-medium',
          trend > 0 ? 'text-red-400' : 'text-neon-green-400'
        )}>
          <TrendingUp className={cn(
            'h-4 w-4',
            trend < 0 && 'rotate-180'
          )} />
          <span>{Math.abs(trend)}%</span>
          <span className="text-gray-500 text-xs ml-1">vs yesterday</span>
        </div>
      )}

      {/* Bottom glow line */}
      <div className={cn(
        'absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-current to-transparent opacity-30',
        statusColors[status]
      )} />
    </motion.div>
  );
}

interface DataPanelProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
  actions?: ReactNode;
}

export function DataPanel({
  title,
  subtitle,
  children,
  icon,
  className,
  actions,
}: DataPanelProps) {
  return (
    <div className={cn('data-panel space-y-4', className)}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          {icon && (
            <div className="p-2 rounded-lg bg-tech-blue-500/10 text-tech-blue-400 border border-tech-blue-500/30">
              {icon}
            </div>
          )}
          <div>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            {subtitle && (
              <p className="text-sm text-gray-400 mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
        {actions && <div>{actions}</div>}
      </div>

      {/* Content */}
      <div className="relative z-10">{children}</div>
    </div>
  );
}

interface StatsGridProps {
  children: ReactNode;
  className?: string;
}

export function StatsGrid({ children, className }: StatsGridProps) {
  return (
    <div className={cn('grid grid-cols-1 gap-4', className)}>
      {children}
    </div>
  );
}

// Predefined metric cards for common use cases
export function PopulationExposureCard({ value, trend }: { value: number; trend?: number }) {
  return (
    <MetricCard
      title="Population Exposure"
      value={value.toLocaleString()}
      unit="people"
      trend={trend}
      icon={<Users className="h-5 w-5" />}
      status={value > 1000000 ? 'danger' : value > 500000 ? 'warning' : 'good'}
      subtitle="At risk population"
      isLive
    />
  );
}

export function RespiratoryRiskCard({ value, trend }: { value: number; trend?: number }) {
  return (
    <MetricCard
      title="Respiratory Risk Index"
      value={value.toFixed(1)}
      trend={trend}
      icon={<Activity className="h-5 w-5" />}
      status={value > 7 ? 'danger' : value > 4 ? 'warning' : 'good'}
      subtitle="Health impact score"
      isLive
    />
  );
}

export function RealtimePM25Card({ value, trend }: { value: number; trend?: number }) {
  return (
    <MetricCard
      title="Real-time PM2.5"
      value={value.toFixed(1)}
      unit="μg/m³"
      trend={trend}
      icon={<Wind className="h-5 w-5" />}
      status={value > 55 ? 'danger' : value > 35 ? 'warning' : 'good'}
      subtitle="Fine particulate matter"
      isLive
    />
  );
}

export function AlertCard({ count, severity }: { count: number; severity: 'high' | 'medium' | 'low' }) {
  const statusMap = {
    high: 'danger' as const,
    medium: 'warning' as const,
    low: 'good' as const,
  };

  return (
    <MetricCard
      title="Active Alerts"
      value={count}
      unit={count === 1 ? 'alert' : 'alerts'}
      icon={<AlertTriangle className="h-5 w-5" />}
      status={statusMap[severity]}
      subtitle={`${severity.charAt(0).toUpperCase() + severity.slice(1)} priority`}
    />
  );
}
