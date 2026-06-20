"use client";

export default function TreasureChest({ size = 16 }: { size?: number }) {
  return (
    <svg viewBox="0 0 16 16" width={size} height={size} aria-label="Treasure Chest">
      {/* Simple chest outline */}
      <rect x="2" y="6" width="12" height="8" fill="none" stroke="#888888" strokeWidth="0.5" />
      <path d="M 2 6 Q 8 2 14 6" fill="none" stroke="#888888" strokeWidth="0.5" />
      <line x1="2" y1="10" x2="14" y2="10" stroke="#888888" strokeWidth="0.5" />
    </svg>
  );
}
