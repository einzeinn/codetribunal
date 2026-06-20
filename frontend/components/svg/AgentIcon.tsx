"use client";

interface AgentIconProps {
  agent: string;
  size?: number;
}

export default function AgentIcon({ agent, size = 32 }: AgentIconProps) {
  const s = size;

  switch (agent.toUpperCase()) {
    case "AEGIS":
      return (
        <svg viewBox="0 0 32 32" width={s} height={s} aria-label="AEGIS">
          {/* Crossed swords — stroke only */}
          <line x1="6" y1="6" x2="26" y2="26" stroke="#c0392b" strokeWidth="1" />
          <line x1="26" y1="6" x2="6" y2="26" stroke="#c0392b" strokeWidth="1" />
        </svg>
      );

    case "ARBITER":
      return (
        <svg viewBox="0 0 32 32" width={s} height={s} aria-label="ARBITER">
          {/* Scales — stroke only */}
          <line x1="16" y1="4" x2="16" y2="28" stroke="#c9a84c" strokeWidth="1.5" />
          <line x1="6" y1="10" x2="26" y2="10" stroke="#c9a84c" strokeWidth="1.5" />
          {/* Left pan */}
          <line x1="6" y1="10" x2="4" y2="20" stroke="#c9a84c" strokeWidth="0.5" />
          <line x1="6" y1="10" x2="10" y2="20" stroke="#c9a84c" strokeWidth="0.5" />
          <circle cx="7" cy="22" r="3" fill="none" stroke="#c9a84c" strokeWidth="0.5" />
          {/* Right pan */}
          <line x1="26" y1="10" x2="22" y2="20" stroke="#c9a84c" strokeWidth="0.5" />
          <line x1="26" y1="10" x2="28" y2="20" stroke="#c9a84c" strokeWidth="0.5" />
          <circle cx="25" cy="22" r="3" fill="none" stroke="#c9a84c" strokeWidth="0.5" />
        </svg>
      );

    case "AXIOM":
      return (
        <svg viewBox="0 0 32 32" width={s} height={s} aria-label="AXIOM">
          {/* Shield — pentagon shape, stroke only */}
          <polygon points="16,4 28,12 26,26 16,30 6,26 4,12" fill="none" stroke="#2980b9" strokeWidth="1" />
        </svg>
      );

    case "METRIC":
      return (
        <svg viewBox="0 0 32 32" width={s} height={s} aria-label="METRIC">
          {/* Bar chart — 3 vertical rectangles */}
          <rect x="4" y="18" width="6" height="10" fill="none" stroke="#888888" strokeWidth="1" />
          <rect x="13" y="12" width="6" height="16" fill="none" stroke="#888888" strokeWidth="1" />
          <rect x="22" y="6" width="6" height="22" fill="none" stroke="#888888" strokeWidth="1" />
        </svg>
      );

    case "LEDGER":
      return (
        <svg viewBox="0 0 32 32" width={s} height={s} aria-label="LEDGER">
          {/* Scroll — rectangle with curved top/bottom ends */}
          <rect x="8" y="6" width="16" height="20" fill="none" stroke="#1a8a8a" strokeWidth="1" />
          <ellipse cx="16" cy="6" rx="10" ry="2" fill="none" stroke="#1a8a8a" strokeWidth="0.5" />
          <ellipse cx="16" cy="26" rx="10" ry="2" fill="none" stroke="#1a8a8a" strokeWidth="0.5" />
        </svg>
      );

    default:
      return (
        <svg viewBox="0 0 32 32" width={s} height={s} aria-label="Unknown">
          <circle cx="16" cy="16" r="10" fill="none" stroke="#888888" strokeWidth="1" />
        </svg>
      );
  }
}
