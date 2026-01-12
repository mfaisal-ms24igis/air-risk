import { useState } from 'react';
import { Menu, Bell, Settings, User, Satellite, Shield, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/authStore';
import { useUserTier } from '@/hooks/useUserTier';
import { motion } from 'framer-motion';

interface CommandCenterHeaderProps {
  onMenuClick?: () => void;
  className?: string;
}

export function CommandCenterHeader({ onMenuClick, className }: CommandCenterHeaderProps) {
  const { user } = useAuthStore();
  const { tier, isPremium } = useUserTier();
  const [notifications] = useState(3);

  return (
    <header className={cn(
      'relative h-16 border-b border-white/10 bg-space-navy-950/80 backdrop-blur-xl',
      className
    )}>
      {/* Scan line effect */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-tech-blue-500/50 to-transparent" />

      <div className="h-full px-6 flex items-center justify-between">
        {/* Left: Logo + Title */}
        <div className="flex items-center gap-6">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
            title="Toggle menu"
          >
            <Menu className="h-5 w-5 text-gray-400" />
          </button>

          <div className="flex items-center gap-4">
            {/* Logo */}
            <div className="relative">
              <img
                src="/Air_RISK_logo.png"
                alt="Air RISK"
                className="h-10 w-auto"
              />
              <div className="absolute inset-0 bg-tech-blue-500/20 blur-xl -z-10" />
            </div>

            {/* Title with tech aesthetic */}
            <div className="hidden md:block">
              <h1 className="text-xl font-bold text-white font-display">
                Air <span className="text-transparent bg-clip-text bg-gradient-to-r from-tech-blue-400 to-neon-green-400">RISK</span>
              </h1>
              <p className="text-xs text-gray-500 font-mono tracking-wider">
                Real-time Intelligence & Spatial Knowledge
              </p>
            </div>
          </div>

          {/* System Status */}
          <div className="hidden lg:flex items-center gap-2 ml-6 px-4 py-2 rounded-lg bg-white/5 border border-neon-green-500/30">
            <Satellite className="h-4 w-4 text-neon-green-400 animate-pulse" />
            <span className="text-xs font-mono text-neon-green-400">SENTINEL-5P</span>
            <div className="relative flex h-2 w-2 ml-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-neon-green-500"></span>
            </div>
          </div>
        </div>

        {/* Right: User info + Actions */}
        <div className="flex items-center gap-4">
          {/* Tier Badge */}
          {isPremium ? (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-tech-blue-500/20 to-neon-green-500/20 border border-tech-blue-500/30">
              <Shield className="h-4 w-4 text-tech-blue-400" />
              <span className="text-xs font-mono font-semibold text-tech-blue-400">PREMIUM</span>
            </div>
          ) : (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
              <span className="text-xs font-mono text-gray-400">BASIC</span>
            </div>
          )}

          {/* Notifications */}
          <button className="relative p-2 rounded-lg hover:bg-white/5 transition-colors group">
            <Bell className="h-5 w-5 text-gray-400 group-hover:text-white transition-colors" />
            {notifications > 0 && (
              <span className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center bg-red-500 text-white text-xs font-bold rounded-full animate-pulse">
                {notifications}
              </span>
            )}
          </button>

          {/* Settings */}
          <button className="p-2 rounded-lg hover:bg-white/5 transition-colors group" title="Settings">
            <Settings className="h-5 w-5 text-gray-400 group-hover:text-white transition-colors" />
          </button>

          {/* User Profile */}
          <div className="flex items-center gap-3 pl-4 border-l border-white/10">
            <div className="hidden md:block text-right">
              <p className="text-sm font-medium text-white">{user?.username || 'User'}</p>
              <p className="text-xs text-gray-500 font-mono">{tier}</p>
            </div>
            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-tech-blue-500 to-neon-green-500 flex items-center justify-center">
              <User className="h-5 w-5 text-white" />
            </div>
          </div>
        </div>
      </div>

      {/* Bottom glow line */}
      <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-tech-blue-500/30 to-transparent" />
    </header>
  );
}

interface StatusBarProps {
  lastUpdate?: Date;
  dataQuality?: number;
  activeSensors?: number;
  className?: string;
}

export function StatusBar({
  lastUpdate = new Date(),
  dataQuality = 98.5,
  activeSensors = 379,
  className,
}: StatusBarProps) {
  return (
    <div className={cn(
      'h-8 px-6 flex items-center justify-between text-xs font-mono bg-space-navy-900/50 border-b border-white/5',
      className
    )}>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Activity className="h-3 w-3 text-neon-green-400" />
          <span className="text-gray-400">System Status:</span>
          <span className="text-neon-green-400 status-online">OPERATIONAL</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-gray-400">Data Quality:</span>
          <span className="text-tech-blue-400">{dataQuality}%</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-gray-400">Active Sensors:</span>
          <span className="text-tech-blue-400">{activeSensors}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 text-gray-500">
        <span>Last Update:</span>
        <span className="text-gray-400">
          {lastUpdate.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          })}
        </span>
      </div>
    </div>
  );
}
