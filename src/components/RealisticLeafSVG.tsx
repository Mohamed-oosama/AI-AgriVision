import React from "react";

export const RealisticLeafSVG = ({ className = "size-14", scan = false }: { className?: string; scan?: boolean }) => (
  <div className="relative inline-block select-none pointer-events-none">
    <svg className={`${className} filter drop-shadow-[0_4px_20px_rgba(4,120,87,0.35)] transition-all hover:scale-105 duration-300`} viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        {/* Deep Forest-to-Emerald Base Gradient */}
        <linearGradient id="leaf-base-grad" x1="100" y1="190" x2="100" y2="10">
          <stop offset="0%" stopColor="#022c22" />
          <stop offset="25%" stopColor="#047857" />
          <stop offset="70%" stopColor="#10b981" />
          <stop offset="100%" stopColor="#34d399" />
        </linearGradient>

        {/* 3D Glossy Highlight Gradient */}
        <linearGradient id="leaf-highlight-grad" x1="70" y1="20" x2="140" y2="180">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.4" />
          <stop offset="30%" stopColor="#ffffff" stopOpacity="0.1" />
          <stop offset="70%" stopColor="#000000" stopOpacity="0.0" />
          <stop offset="100%" stopColor="#000000" stopOpacity="0.25" />
        </linearGradient>

        {/* Veins Glowing Mint Gradient */}
        <linearGradient id="leaf-vein-grad" x1="100" y1="185" x2="100" y2="20">
          <stop offset="0%" stopColor="#064e3b" />
          <stop offset="50%" stopColor="#6ee7b7" />
          <stop offset="100%" stopColor="#a7f3d0" />
        </linearGradient>

        {/* Outer Glow Filter */}
        <filter id="leaf-outer-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Dewdrop Gradient */}
        <linearGradient id="dewdrop-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.8" />
          <stop offset="50%" stopColor="#ffffff" stopOpacity="0.1" />
          <stop offset="100%" stopColor="#047857" stopOpacity="0.4" />
        </linearGradient>
      </defs>

      {/* 1. Outer Glowing Contour */}
      <path
        d="M 100,185 C 45,155 25,115 35,70 C 42,40 72,25 100,15 C 128,25 158,40 165,70 C 175,115 155,155 100,185 Z"
        stroke="#34d399"
        strokeWidth="3"
        strokeLinecap="round"
        filter="url(#leaf-outer-glow)"
        opacity="0.55"
      />

      {/* 2. Main Leaf Blade Body */}
      <path
        d="M 100,185 C 45,155 25,115 35,70 C 42,40 72,25 100,15 C 128,25 158,40 165,70 C 175,115 155,155 100,185 Z"
        fill="url(#leaf-base-grad)"
        stroke="#047857"
        strokeWidth="1.5"
      />

      {/* 3. 3D Glossy Overlay (light/shade depth) */}
      <path
        d="M 100,185 C 45,155 25,115 35,70 C 42,40 72,25 100,15 C 128,25 158,40 165,70 C 175,115 155,155 100,185 Z"
        fill="url(#leaf-highlight-grad)"
      />

      {/* 4. Fine Veinlet Network (Neural Network texture) */}
      <g stroke="#6ee7b7" strokeWidth="0.6" opacity="0.3" strokeLinecap="round">
        {/* Veinlets Left */}
        <path d="M 68,145 C 64,138 60,135 56,134" />
        <path d="M 52,112 C 45,108 42,102 44,95" />
        <path d="M 45,82 C 40,78 38,72 40,65" />
        <path d="M 50,56 C 45,50 44,44 48,40" />
        
        {/* Veinlets Right */}
        <path d="M 132,145 C 136,138 140,135 144,134" />
        <path d="M 148,112 C 155,108 158,102 156,95" />
        <path d="M 155,82 C 160,78 162,72 160,65" />
        <path d="M 150,56 C 155,50 156,44 152,40" />

        {/* Secondary branches */}
        <path d="M 78,118 C 72,112 68,112 64,114" />
        <path d="M 122,118 C 128,112 132,112 136,114" />
        <path d="M 72,88 C 65,82 60,82 54,85" />
        <path d="M 128,88 C 135,82 140,82 146,85" />
      </g>

      {/* 5. Primary Lateral Veins */}
      <g stroke="url(#leaf-vein-grad)" strokeWidth="1.8" strokeLinecap="round" opacity="0.85">
        {/* Lateral Veins - Left */}
        <path d="M 100,160 C 80,154 62,142 58,134" />
        <path d="M 100,138 C 76,128 52,110 46,98" />
        <path d="M 100,112 C 72,98 48,78 42,62" />
        <path d="M 100,85 C 70,70 48,48 46,32" />
        <path d="M 100,58 C 75,44 58,26 56,16" />

        {/* Lateral Veins - Right */}
        <path d="M 100,160 C 120,154 138,142 142,134" />
        <path d="M 100,138 C 124,128 148,110 154,98" />
        <path d="M 100,112 C 128,98 152,78 158,62" />
        <path d="M 100,85 C 130,70 152,48 154,32" />
        <path d="M 100,58 C 125,44 142,26 144,16" />
      </g>

      {/* 6. Main Midrib Stem */}
      <path d="M 100,192 C 100,150 100,45 100,14" stroke="url(#leaf-vein-grad)" strokeWidth="3.5" strokeLinecap="round" />

      {/* 7. Realistic Shiny Dewdrops */}
      {/* Dewdrop 1 - Bottom Left */}
      <g transform="translate(62, 125)">
        <ellipse cx="0" cy="0" rx="5" ry="4" fill="url(#dewdrop-grad)" filter="drop-shadow(0 1.5px 2px rgba(2,44,34,0.4))" />
        <circle cx="-1.8" cy="-1.2" r="1" fill="#ffffff" opacity="0.9" />
      </g>
      
      {/* Dewdrop 2 - Top Right */}
      <g transform="translate(132, 75)">
        <ellipse cx="0" cy="0" rx="4" ry="3" fill="url(#dewdrop-grad)" filter="drop-shadow(0 1.5px 2px rgba(2,44,34,0.4))" />
        <circle cx="-1.5" cy="-0.8" r="0.8" fill="#ffffff" opacity="0.9" />
      </g>
    </svg>

    {/* Sci-Fi Scanning Overlay Beam */}
    {scan && (
      <div className="absolute inset-x-2 inset-y-1.5 pointer-events-none overflow-hidden rounded-[50%_40%_50%_40%]">
        <div className="w-full h-1 bg-emerald-400 shadow-[0_0_12px_#10b981,0_0_24px_#34d399] opacity-90 animate-[scan_2s_ease-in-out_infinite]" />
      </div>
    )}

    {/* Keyframe animation injection */}
    <style>{`
      @keyframes scan {
        0%, 100% { top: 12%; opacity: 0.2; }
        50% { top: 88%; opacity: 0.95; }
      }
    `}</style>
  </div>
);
