"use client";

import { useEffect, useRef } from "react";
import MessageEntry from "./MessageEntry";

export interface ProceedingFinding {
  finding_id: string;
  agent: string;
  category: string;
  severity: string;
  line_range: [number, number];
  claim: string;
  evidence_source: string;
  confidence: number;
  withdrawn?: boolean;
}

export interface Proceeding {
  agent: string;
  tag: string;
  message: string;
  round_number: number;
  timestamp: string;
  confidence: number;
  // New structured metadata
  phase?: string;
  speaker?: string;
  exhibit_ref?: string;
  is_objection?: boolean;
  line_range?: [number, number];
  findings?: ProceedingFinding[];
  rubric_scores?: {
    security: number;
    performance: number;
    maintainability: number;
    verdict?: string;
  };
}

interface ProceedingsFeedProps {
  proceedings: Proceeding[];
  isTyping: boolean;
  isConnected: boolean;
  currentPhase?: string;
}

export default function ProceedingsFeed({ proceedings, isTyping, isConnected }: ProceedingsFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [proceedings.length, isTyping]);

  return (
    <div className="flex-1 overflow-hidden flex flex-col">
      {/* Scrollable message area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden min-w-0">
        {/* Empty state */}
        {proceedings.length === 0 && !isConnected && (
          <div className="py-8 text-center font-[family-name:var(--font-im-fell)] text-[13px] text-text-disabled italic">
            Awaiting tribunal proceedings...
          </div>
        )}

        {proceedings.length === 0 && isConnected && (
          <div className="py-8 text-center">
            <div className="inline-block w-6 h-6 border border-gold border-t-transparent rounded-full animate-spin" />
            <p className="font-[family-name:var(--font-im-fell)] text-text-secondary mt-2 text-sm">Summoning the court officers...</p>
          </div>
        )}

        {/* Messages */}
        <div className="w-full">
          {proceedings.map((p, i) => (
            <MessageEntry
              key={`${p.agent}-${p.round_number}-${i}`}
              agent={p.agent}
              tag={p.tag}
              message={p.message}
              roundNumber={p.round_number}
              phase={p.phase}
              exhibitRef={p.exhibit_ref}
              isObjection={p.is_objection}
              findings={p.findings}
              lineRange={p.line_range}
            />
          ))}
        </div>

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex items-center gap-2 px-4 py-3 animate-fade-in">
            <div className="flex gap-1">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
            <span className="font-[family-name:var(--font-im-fell)] text-xs text-text-secondary italic">Agent is addressing the court...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
