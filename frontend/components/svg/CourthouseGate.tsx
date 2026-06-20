"use client";

export default function CourthouseGate() {
  return (
    <svg viewBox="0 0 200 160" className="w-64 h-48 md:w-80 md:h-60" aria-label="Courthouse Gate">
      {/* Two pillars */}
      <rect x="40" y="40" width="28" height="100" fill="#080808" stroke="#2a2a2a" strokeWidth="0.5" />
      <rect x="132" y="40" width="28" height="100" fill="#080808" stroke="#2a2a2a" strokeWidth="0.5" />

      {/* Arch */}
      <path d="M 50 80 Q 100 20 150 80" fill="none" stroke="#2a2a2a" strokeWidth="0.5" />

      {/* 5 vertical bars inside arch */}
      {[70, 85, 100, 115, 130].map((x, i) => (
        <line key={i} x1={x} y1={75} x2={x} y2={140} stroke="#2a2a2a" strokeWidth="0.5" />
      ))}

      {/* 1 horizontal crossbar */}
      <line x1="68" y1="110" x2="132" y2="110" stroke="#2a2a2a" strokeWidth="0.5" />

      {/* Torch brackets — simple L-shapes */}
      <path d="M 38 65 L 32 65 L 32 75" fill="none" stroke="#2a2a2a" strokeWidth="0.5" />
      <path d="M 162 65 L 168 65 L 168 75" fill="none" stroke="#2a2a2a" strokeWidth="0.5" />

      {/* Flames — small ellipses */}
      <ellipse cx="32" cy="60" rx="3" ry="5" fill="#c9a84c" opacity="0.7" className="animate-flame" />
      <ellipse cx="32" cy="59" rx="4" ry="6" fill="#c9a84c" opacity="0.3" className="animate-flame" />
      <ellipse cx="168" cy="60" rx="3" ry="5" fill="#c9a84c" opacity="0.7" className="animate-flame" style={{ animationDelay: "0.5s" }} />
      <ellipse cx="168" cy="59" rx="4" ry="6" fill="#c9a84c" opacity="0.3" className="animate-flame" style={{ animationDelay: "0.5s" }} />

      {/* Scale of justice at arch apex */}
      <line x1="100" y1="10" x2="100" y2="30" stroke="#c9a84c" strokeWidth="0.5" />
      <line x1="92" y1="18" x2="108" y2="18" stroke="#c9a84c" strokeWidth="0.5" />
      {/* Left pan */}
      <line x1="92" y1="18" x2="89" y2="28" stroke="#c9a84c" strokeWidth="0.5" />
      <line x1="92" y1="18" x2="95" y2="28" stroke="#c9a84c" strokeWidth="0.5" />
      <circle cx="92" cy="30" r="3" fill="none" stroke="#c9a84c" strokeWidth="0.5" />
      {/* Right pan */}
      <line x1="108" y1="18" x2="105" y2="28" stroke="#c9a84c" strokeWidth="0.5" />
      <line x1="108" y1="18" x2="111" y2="28" stroke="#c9a84c" strokeWidth="0.5" />
      <circle cx="108" cy="30" r="3" fill="none" stroke="#c9a84c" strokeWidth="0.5" />
    </svg>
  );
}
