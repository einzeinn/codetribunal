"use client";

interface ScoreBarProps {
  label: string;
  score: number;
  maxScore?: number;
  color: string;
}

export default function ScoreBar({ label, score, maxScore = 10, color }: ScoreBarProps) {
  const pct = Math.min(100, (score / maxScore) * 100);
  return (
    <div className="flex items-center gap-2 w-full">
      {/* Label */}
      <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary uppercase tracking-wider w-20 text-left flex-shrink-0 truncate">
        {label}
      </span>
      {/* Bar — 2px height */}
      <div className="flex-1 h-0.5 bg-[#2a1f08] relative overflow-hidden">
        <div
          className="h-full animate-score-fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {/* Number */}
      <span className="font-[family-name:var(--font-cinzel)] text-[11px] text-gold w-8 text-right flex-shrink-0">
        {score.toFixed(1)}
      </span>
    </div>
  );
}
