"use client";

import AgentIcon from "../svg/AgentIcon";
import StatusBadge from "../ui/StatusBadge";

interface AgentCardProps {
  name: string;
  role: string;
  status: string;
  isActive: boolean;
  isCenter?: boolean;
}

export default function AgentCard({ name, role, status, isActive, isCenter }: AgentCardProps) {
  return (
    <div
      className={`flex flex-col items-center gap-1 px-3 py-2 min-w-[80px] transition-all duration-200 ${
        isCenter ? "min-w-[90px] border-t border-gold" : ""
      }`}
    >
      {/* Agent icon on transparent background */}
      <div className={`p-1.5 ${isActive ? "bg-gold/10" : ""}`}>
        <AgentIcon agent={name} size={isCenter ? 40 : 32} />
      </div>
      <span className="font-[family-name:var(--font-cinzel)] text-[8px] text-text-secondary tracking-[0.2em] uppercase leading-none">
        {role}
      </span>
      <span className={`font-[family-name:var(--font-cinzel)] text-[11px] text-gold tracking-[0.1em] leading-none ${isCenter ? "text-[13px]" : ""}`}>
        {name}
      </span>
      <StatusBadge status={status} />
    </div>
  );
}
