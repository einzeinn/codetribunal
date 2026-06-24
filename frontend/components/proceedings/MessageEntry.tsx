"use client";

import AgentIcon from "../svg/AgentIcon";
import TagBadge from "../ui/TagBadge";
import type { ProceedingFinding } from "./ProceedingsFeed";

interface MessageEntryProps {
  agent: string;
  tag: string;
  message: string;
  roundNumber: number;
  phase?: string;
  exhibitRef?: string;
  isObjection?: boolean;
  findings?: ProceedingFinding[];
  lineRange?: [number, number];
}

const PHASE_LABELS: Record<string, string> = {
  investigation: "OPENING STATEMENTS",
  conflict_detection: "EVIDENCE REVIEW",
  cross_examination: "CROSS-EXAMINATION",
  verdict: "FINAL RULING",
  complete: "SESSION COMPLETE",
};

export default function MessageEntry({
  agent, tag, message, roundNumber,
  phase, exhibitRef, isObjection, findings,
}: MessageEntryProps) {
  const isSpeakingRole = agent === "AEGIS" || agent === "AXIOM";
  const showPhaseBanner = phase && PHASE_LABELS[phase];

  return (
    <div className="animate-fade-in">
      {/* Phase banner */}
      {showPhaseBanner && (
        <div className={`phase-banner px-4 py-1.5 text-center ${phase === "verdict" ? "phase-verdict" : ""}`}>
          <span className="font-[family-name:var(--font-cinzel)] text-[9px] tracking-[0.3em] uppercase text-gold">
            {PHASE_LABELS[phase]}
          </span>
        </div>
      )}

      {/* Objection flash overlay */}
      {isObjection && (
        <div className="objection-flash">
          <span className="font-[family-name:var(--font-cinzel-decorative)] text-[28px] text-[#8b2020] tracking-[0.2em]">
            OBJECTION!
          </span>
        </div>
      )}

      {/* Main message */}
      <div className={`flex gap-3 py-4 border-b border-[#1a1a1a] max-w-full overflow-hidden ${
        tag === "Phase Transition" ? "opacity-60" : ""
      }`}>
        {/* Agent icon */}
        <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-gold/10">
          <AgentIcon agent={agent} size={14} />
        </div>

        <div className="flex-1 min-w-0 overflow-hidden">
          {/* Header row */}
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-[family-name:var(--font-cinzel)] text-[11px] text-gold tracking-[0.1em]">
              {agent}
            </span>
            <TagBadge tag={tag} />
            {roundNumber > 0 && (
              <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-disabled">
                R{roundNumber}
              </span>
            )}
            {/* Exhibit reference badge */}
            {exhibitRef && (
              <span className="exhibit-badge">
                {exhibitRef}
              </span>
            )}
          </div>

          {/* Message text */}
          <p className={`text-[13px] text-text-primary leading-[1.7] whitespace-pre-wrap break-words overflow-wrap ${
            isSpeakingRole ? "italic" : ""
          }`}>
            {message}
          </p>

          {/* Structured findings summary */}
          {findings && findings.length > 0 && (
            <div className="mt-2 space-y-1">
              {findings.slice(0, 3).map((f) => (
                <div key={f.finding_id} className="flex items-start gap-2 text-[10px]">
                  <span className={`flex-shrink-0 w-1.5 h-1.5 mt-1 rounded-full ${
                    f.severity === "critical" || f.severity === "high"
                      ? "bg-[#8b2020]"
                      : f.severity === "medium"
                      ? "bg-gold"
                      : "bg-[#2a2a2a]"
                  }`} />
                  <span className="text-text-secondary leading-snug">
                    <span className="text-gold font-[family-name:var(--font-jetbrains)]">
                      L{f.line_range[0]}-{f.line_range[1]}
                    </span>{" "}
                    {f.evidence_source && (
                      <span className="text-text-disabled">
                        [{f.evidence_source}]{" "}
                      </span>
                    )}
                    {f.claim.length > 80 ? f.claim.slice(0, 80) + "..." : f.claim}
                    {f.withdrawn && (
                      <span className="text-[#8b2020] ml-1">[WITHDRAWN]</span>
                    )}
                  </span>
                </div>
              ))}
              {findings.length > 3 && (
                <span className="text-[10px] text-text-disabled">
                  +{findings.length - 3} more findings
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
