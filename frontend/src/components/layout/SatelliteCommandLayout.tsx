import { ReactNode } from 'react';
import { CommandCenterHeader, StatusBar } from './CommandCenterHeader';
import { cn } from '@/lib/utils';

interface SatelliteCommandLayoutProps {
  children: ReactNode;
  sidebar?: ReactNode;
  rightPanel?: ReactNode;
  className?: string;
}

export function SatelliteCommandLayout({
  children,
  sidebar,
  rightPanel,
  className,
}: SatelliteCommandLayoutProps) {
  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-space-navy-950">
      {/* Tech grid background */}
      <div className="fixed inset-0 bg-tech-grid opacity-50 pointer-events-none" />
      
      {/* Radial gradient overlays */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-0 w-1/2 h-1/2 bg-gradient-radial from-tech-blue-500/10 to-transparent blur-3xl" />
        <div className="absolute bottom-0 right-0 w-1/2 h-1/2 bg-gradient-radial from-neon-green-500/10 to-transparent blur-3xl" />
      </div>

      {/* Header */}
      <CommandCenterHeader />
      
      {/* Status Bar */}
      <StatusBar />

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar (optional) */}
        {sidebar && (
          <aside className="w-64 border-r border-white/10 bg-space-navy-950/50 backdrop-blur-sm overflow-y-auto">
            {sidebar}
          </aside>
        )}

        {/* Main Content Area */}
        <main className={cn('flex-1 relative overflow-hidden', className)}>
          {children}
        </main>

        {/* Right Data Panel */}
        {rightPanel && (
          <aside className="w-96 border-l border-white/10 bg-space-navy-950/80 backdrop-blur-xl overflow-y-auto">
            <div className="p-6 space-y-6">
              {rightPanel}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
