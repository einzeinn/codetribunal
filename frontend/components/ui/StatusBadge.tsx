"use client";

interface StatusBadgeProps {
  status: string;
}

const statusColors: Record<string, string> = {
  Speaking: "bg-[#0a1a0a] text-[#7ab848] border-[#2a3a2a]",
  Presiding: "bg-[#1a1a0a] text-[#c9a84c] border-[#3a3a1a]",
  Objecting: "bg-[#1a0a0a] text-[#c0392b] border-[#3a1a1a]",
  "On Standby": "bg-transparent text-[#555555] border-[#2a2a2a]",
  Awaiting: "bg-transparent text-[#555555] border-[#2a2a2a]",
  Recording: "bg-[#0a1a1a] text-[#1a8a8a] border-[#1a3a3a]",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colors = statusColors[status] || statusColors["On Standby"];
  return (
    <span className={`inline-block px-2 py-0.5 font-[family-name:var(--font-cinzel)] text-[9px] uppercase tracking-[0.15em] border ${colors}`}>
      {status}
    </span>
  );
}
