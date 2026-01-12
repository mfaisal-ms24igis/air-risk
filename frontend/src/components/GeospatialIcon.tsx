/**
 * Geospatial Icon Component
 * 
 * SVG icon for Air RISK branding with satellite and grid pattern.
 * @module components/GeospatialIcon
 */

interface GeospatialIconProps {
  size?: number;
  className?: string;
}

export function GeospatialIcon({ size = 64, className = '' }: GeospatialIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Globe/Shield background */}
      <path
        d="M80 30 Q120 20 140 50 Q160 80 150 130 Q130 160 80 170 Q40 160 30 130 Q20 80 40 50 Q60 20 80 30 Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-blue-500"
      />
      
      {/* Grid pattern */}
      <g className="text-blue-500" opacity="0.8">
        <line x1="50" y1="50" x2="130" y2="70" stroke="currentColor" strokeWidth="1.5" />
        <line x1="50" y1="70" x2="135" y2="90" stroke="currentColor" strokeWidth="1.5" />
        <line x1="50" y1="90" x2="140" y2="110" stroke="currentColor" strokeWidth="1.5" />
        <line x1="55" y1="110" x2="135" y2="130" stroke="currentColor" strokeWidth="1.5" />
        <line x1="70" y1="130" x2="110" y2="145" stroke="currentColor" strokeWidth="1.5" />
        
        {/* Vertical grid lines */}
        <line x1="65" y1="50" x2="95" y2="130" stroke="currentColor" strokeWidth="1.5" />
        <line x1="85" y1="45" x2="120" y2="130" stroke="currentColor" strokeWidth="1.5" />
        <line x1="105" y1="42" x2="140" y2="128" stroke="currentColor" strokeWidth="1.5" />
        <line x1="125" y1="50" x2="145" y2="125" stroke="currentColor" strokeWidth="1.5" />
      </g>

      {/* Right side gradient to green */}
      <g className="text-cyan-400" opacity="0.6">
        <line x1="120" y1="60" x2="150" y2="90" stroke="currentColor" strokeWidth="1.5" />
        <line x1="130" y1="80" x2="150" y2="115" stroke="currentColor" strokeWidth="1.5" />
        <line x1="135" y1="100" x2="145" y2="135" stroke="currentColor" strokeWidth="1.5" />
      </g>

      {/* Satellite */}
      <g className="text-blue-400">
        {/* Satellite body */}
        <rect x="140" y="25" width="35" height="25" rx="3" stroke="currentColor" strokeWidth="2" fill="none" />
        
        {/* Solar panels */}
        <rect x="125" y="20" width="12" height="8" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <rect x="177" y="20" width="12" height="8" stroke="currentColor" strokeWidth="1.5" fill="none" />
        
        {/* Connection to globe */}
        <path
          d="M150 50 Q160 60 150 80"
          stroke="currentColor"
          strokeWidth="2.5"
          fill="none"
          strokeLinecap="round"
          className="text-blue-400"
        />
      </g>
    </svg>
  );
}

export default GeospatialIcon;
