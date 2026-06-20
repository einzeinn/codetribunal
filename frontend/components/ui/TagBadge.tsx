"use client";

const tagColors: Record<string, string> = {
  Opening: "bg-[#0a1a2a] text-[#5a8ab0]",
  Objection: "bg-[#1a0a0a] text-[#c0392b]",
  Evidence: "bg-[#1a1a0a] text-[#c9a84c]",
  Sustained: "bg-[#0a1a0a] text-[#4a8a4a]",
  "Counter-Argument": "bg-[#0a0a1a] text-[#5a5a9a]",
  "Final Verdict": "bg-[#1a1a0a] text-[#c9a84c] border border-[#c9a84c]",
  "Case Filed": "bg-transparent text-[#555555]",
  Recording: "bg-transparent text-[#555555]",
};

export default function TagBadge({ tag }: { tag: string }) {
  const colors = tagColors[tag] || "bg-transparent text-[#555555]";
  return (
    <span className={`inline-block px-2 py-0.5 font-[family-name:var(--font-cinzel)] text-[9px] uppercase tracking-[0.15em] ${colors}`}>
      {tag}
    </span>
  );
}
