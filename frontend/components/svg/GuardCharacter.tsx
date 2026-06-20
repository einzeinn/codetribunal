"use client";

export default function GuardCharacter() {
  return (
    <svg viewBox="0 0 100 160" className="w-40 h-64 md:w-48 md:h-80" aria-label="Guard">
      {/* Helmet — ellipse 36x28 at top */}
      <ellipse cx="50" cy="28" rx="18" ry="14" fill="#1a1a1a" />
      {/* Visor rim */}
      <rect x="36" y="26" width="28" height="8" fill="#151515" />
      {/* Red plume */}
      <path d="M 50 14 Q 48 8 52 4 Q 56 8 54 14" fill="#6b1515" />

      {/* Body — torso rect */}
      <rect x="35" y="42" width="30" height="40" fill="#1a1a1a" />
      {/* Center seam */}
      <line x1="50" y1="42" x2="50" y2="82" stroke="#2a2a2a" strokeWidth="0.5" />
      {/* Pauldrons */}
      <rect x="30" y="42" width="8" height="12" fill="#1a1a1a" />
      <rect x="62" y="42" width="8" height="12" fill="#1a1a1a" />

      {/* Arms — two rects extending sideways */}
      <rect x="22" y="48" width="12" height="8" fill="#1a1a1a" />
      <rect x="66" y="48" width="12" height="8" fill="#1a1a1a" />

      {/* Spear — vertical line full height */}
      <line x1="82" y1="10" x2="82" y2="150" stroke="#555555" strokeWidth="1" />
      {/* Triangle tip */}
      <polygon points="82,10 78,22 86,22" fill="#888888" />

      {/* Legs — two rects */}
      <rect x="38" y="82" width="12" height="36" fill="#1a1a1a" />
      <rect x="50" y="82" width="12" height="36" fill="#1a1a1a" />

      {/* Boots — slightly wider rects */}
      <rect x="36" y="118" width="14" height="10" fill="#151515" />
      <rect x="50" y="118" width="14" height="10" fill="#151515" />

      {/* Gold accent lines on armor */}
      <line x1="35" y1="42" x2="65" y2="42" stroke="#c9a84c" strokeWidth="0.5" />
      <line x1="35" y1="82" x2="65" y2="82" stroke="#c9a84c" strokeWidth="0.5" />
    </svg>
  );
}
