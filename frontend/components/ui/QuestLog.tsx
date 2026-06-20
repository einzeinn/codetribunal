"use client";

import TreasureChest from "../svg/TreasureChest";

interface QuestItem {
  text: string;
  completed: boolean;
}

interface QuestLogProps {
  items: QuestItem[];
  currentObjective: string;
}

export default function QuestLog({ items, currentObjective }: QuestLogProps) {
  return (
    <div className="pl-4 border-l border-[#2a2a2a]">
      {/* QUEST LOG title */}
      <h3 className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase mb-4">
        QUEST LOG
      </h3>

      {/* Quest items with diamond bullets */}
      <ul className="space-y-2.5 mb-4">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-2 text-xs min-w-0">
            {item.completed ? (
              // Diamond filled (8px)
              <svg width="8" height="8" viewBox="0 0 8 8" className="flex-shrink-0">
                <rect x="2" y="2" width="4" height="4" fill="#c9a84c" transform="rotate(45 4 4)" />
              </svg>
            ) : (
              // Circle outline (8px)
              <svg width="8" height="8" viewBox="0 0 8 8" className="flex-shrink-0">
                <circle cx="4" cy="4" r="3" fill="none" stroke="#2a2a2a" strokeWidth="0.5" />
              </svg>
            )}
            <span
              className={`font-[family-name:var(--font-im-fell)] text-[12px] leading-tight truncate ${
                item.completed ? "text-text-secondary line-through decoration-[#2a2a2a]" : "text-text-disabled"
              }`}
            >
              {item.text}
            </span>
          </li>
        ))}
      </ul>

      {/* Divider */}
      <div className="h-px bg-[#1a1a1a] my-4" />

      {/* Current Objective */}
      <h4 className="font-[family-name:var(--font-cinzel)] text-[8px] text-text-secondary tracking-[0.15em] uppercase mb-1.5">
        Current Objective
      </h4>
      <p className="font-[family-name:var(--font-im-fell)] text-[12px] text-text-primary italic leading-snug break-words">
        {currentObjective}
      </p>

      {/* Reward section */}
      <div className="mt-4 flex items-center gap-2">
        <TreasureChest size={16} />
        <span className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-secondary">A fair and just verdict</span>
      </div>
    </div>
  );
}
