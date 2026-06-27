"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import CourtroomCharacter from "./CourtroomCharacter";
import { AGENTS, toAgentId, type AgentId } from "../../lib/courtroom-theme";

/* ─── Types ─── */

interface LedgerEntry {
  id: string;
  text: string;
  timestamp: string;
}

interface CourtroomStageProps {
  /** Currently speaking agent (uppercase backend name), empty = idle */
  activeSpeaker: string;
  /** Current dialogue text for the active speaker */
  activeDialogue: string | null;
  /** Current trial phase */
  currentPhase: string;
  /** Is an agent currently typing */
  isTyping: boolean;
  /** Rubric scores */
  scores: { security: number; performance: number; maintainability: number };
  /** Whether the trial is complete */
  isComplete: boolean;
  /** ARBITER verdict text (shown when complete) */
  verdictText?: string;
  /** Verdict word (APPROVED / REJECTED / etc.) */
  rubricVerdict?: string | null;
  /** Conflict clusters for LEDGER tracking */
  conflictCount?: number;
  /** Callback: user wants to see full verdict modal */
  onRequestVerdict?: () => void;
  /** Callback: user wants new case */
  onNewCase?: () => void;
  /** Token usage for display */
  tokenCount?: number;
}

/* ─── LEDGER Toast ─── */

function LedgerToast({ entry, onDone }: { entry: LedgerEntry; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 1800);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <motion.div
      className="fixed bottom-6 left-1/2 z-50"
      style={{ x: "-50%" }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      <div className="bg-bg-surface border border-gold/30 px-4 py-2 text-[11px] text-gold font-[family-name:var(--font-cinzel)] tracking-[0.1em]">
        LEDGER: {entry.text}
      </div>
    </motion.div>
  );
}

/* ─── LEDGER Log Panel ─── */

function LedgerPanel({
  isOpen,
  onClose,
  entries,
}: {
  isOpen: boolean;
  onClose: () => void;
  entries: LedgerEntry[];
}) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-40 bg-black/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          {/* Panel */}
          <motion.div
            className="fixed top-0 right-0 bottom-0 z-50 w-[320px] bg-bg-surface border-l border-border-default"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "tween", duration: 0.3 }}
          >
            <div className="p-4 border-b border-border-default flex items-center justify-between">
              <span className="font-[family-name:var(--font-cinzel)] text-[10px] text-gold tracking-[0.2em] uppercase">
                LEDGER — Session Log
              </span>
              <button onClick={onClose} className="text-text-secondary hover:text-text-primary text-sm">
                ✕
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(100vh-60px)]">
              {entries.length === 0 ? (
                <p className="text-[12px] text-text-disabled italic font-[family-name:var(--font-im-fell)]">
                  No entries recorded yet.
                </p>
              ) : (
                <div className="space-y-3">
                  {[...entries].reverse().map((e) => (
                    <div key={e.id} className="border-b border-border-default/50 pb-2">
                      <p className="text-[11px] text-text-primary font-[family-name:var(--font-im-fell)]">
                        {e.text}
                      </p>
                      <span className="text-[9px] text-text-disabled font-[family-name:var(--font-jetbrains)]">
                        {e.timestamp}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/* ─── Phase Progress ─── */

const PHASE_ORDER = ["investigation", "conflict_detection", "cross_examination", "verdict", "complete"];

function PhaseProgress({ currentPhase }: { currentPhase: string }) {
  const idx = PHASE_ORDER.indexOf(currentPhase);
  return (
    <div className="flex gap-1 items-center max-w-[300px] mx-auto">
      {PHASE_ORDER.slice(0, -1).map((phase, i) => (
        <div
          key={phase}
          className="flex-1 h-[2px] transition-colors duration-500"
          style={{
            background:
              i < idx ? "var(--gold)" : i === idx ? "var(--gold)" : "var(--border-default)",
            opacity: i < idx ? 0.5 : 1,
          }}
        />
      ))}
    </div>
  );
}

/* ─── ARBITER Overlay ─── */

function ArbiterOverlay({
  dialogue,
  onClose,
}: {
  dialogue: string | null;
  onClose?: () => void;
}) {
  return (
    <motion.div
      className="absolute inset-0 z-30 flex items-center justify-center"
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: -20, opacity: 0 }}
      transition={{ type: "spring", bounce: 0.3, duration: 0.5 }}
    >
      {/* Dimmed backdrop — 3 panels still visible behind */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
        role="button"
        tabIndex={-1}
      />

      {/* ARBITER character centered */}
      <div className="relative z-10 w-[200px] md:w-[260px]">
        <CourtroomCharacter
          agentId="arbiter"
          pose="active"
          isSpeaking
          dialogue={dialogue}
        />
      </div>
    </motion.div>
  );
}

/* ─── Main CourtroomStage ─── */

export default function CourtroomStage({
  activeSpeaker,
  activeDialogue,
  currentPhase,
  isTyping,
  scores,
  isComplete,
  verdictText,
  rubricVerdict,
  conflictCount = 0,
  onRequestVerdict,
  onNewCase,
  tokenCount,
}: CourtroomStageProps) {
  const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>([]);
  const [isLedgerOpen, setIsLedgerOpen] = useState(false);
  const [currentToast, setCurrentToast] = useState<LedgerEntry | null>(null);

  // Track significant events for LEDGER
  const addLedgerEntry = useCallback((text: string) => {
    const entry: LedgerEntry = {
      id: `ledger-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      text,
      timestamp: new Date().toLocaleTimeString(),
    };
    setLedgerEntries((prev) => [...prev, entry]);
    setCurrentToast(entry);
  }, []);

  // Auto-trigger LEDGER entries on phase transitions
  const prevPhase = useRef(currentPhase);
  useEffect(() => {
    if (currentPhase !== prevPhase.current) {
      prevPhase.current = currentPhase;
      if (currentPhase === "cross_examination") {
        addLedgerEntry("Cross-examination commenced");
      } else if (currentPhase === "verdict") {
        addLedgerEntry("ARBITER is delivering the verdict");
      } else if (currentPhase === "complete") {
        addLedgerEntry("Session complete — verdict rendered");
      }
    }
  }, [currentPhase, addLedgerEntry]);

  // Determine active speaker agent id
  const speakerId: AgentId | null = activeSpeaker
    ? toAgentId(activeSpeaker)
    : null;
  const isArbiterActive = speakerId === "arbiter";

  // Agent poses
  const getAgentState = (id: AgentId) => ({
    pose: speakerId === id ? "active" as const : "neutral" as const,
    isSpeaking: speakerId === id,
    dialogue: speakerId === id ? activeDialogue : null,
  });

  return (
    <div className="relative w-full h-full min-h-screen flex flex-col overflow-hidden">
      {/* Background layer — dark mahogany gradient */}
      <div
        className="absolute inset-0 z-0"
        style={{
          background: "linear-gradient(180deg, #1a1a1a 0%, #1e1812 40%, #2a2418 100%)",
        }}
      />
      {/* Decorative border accents */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gold/10" />
        <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gold/10" />
        <div className="absolute top-0 left-0 bottom-0 w-[1px] bg-gold/5" />
        <div className="absolute top-0 right-0 bottom-0 w-[1px] bg-gold/5" />
      </div>

      {/* ─── HEADER ─── */}
      <header className="relative z-10 text-center py-3 border-b border-border-default/30 flex-shrink-0">
        <h1 className="font-[family-name:var(--font-cinzel)] text-[13px] text-gold tracking-[4px]">
          CODE TRIBUNAL
        </h1>
        {!isComplete && (
          <p className="font-[family-name:var(--font-im-fell)] text-[10px] text-[#4a8a4a] mt-0.5 flex items-center justify-center gap-1">
            <span className="inline-block w-1.5 h-1.5 bg-[#4a8a4a] rounded-full animate-pulse-live" />
            Live
          </p>
        )}
        <div className="mt-2">
          <PhaseProgress currentPhase={currentPhase} />
        </div>
      </header>

      {/* ─── MAIN STAGE ─── */}
      <div className="relative z-10 flex-1 flex flex-col min-h-0">
        {/* Tier 1: 3 panels — AEGIS, AXIOM, METRIC */}
        <div className="flex-1 grid grid-cols-3 gap-2 p-3 min-h-0">
          {(["aegis", "axiom", "metric"] as AgentId[]).map((id) => {
            const state = getAgentState(id);
            const theme = AGENTS[id];
            return (
              <motion.div
                key={id}
                className="relative flex flex-col items-center justify-end overflow-hidden"
                animate={{
                  scale: state.isSpeaking ? 1.03 : 1,
                  opacity: isArbiterActive ? 0.3 : 1,
                }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                style={{
                  borderColor: state.isSpeaking ? theme.accent : "transparent",
                  borderWidth: 1,
                  borderStyle: "solid",
                  boxShadow: state.isSpeaking
                    ? `0 0 20px rgba(${theme.accentRgb}, 0.15)`
                    : "none",
                }}
              >
                {/* Agent name badge above sprite */}
                <div
                  className="absolute top-2 left-2 z-10 px-2 py-0.5"
                  style={{
                    background: `rgba(${theme.accentRgb}, 0.1)`,
                    borderBottom: `1px solid ${theme.accent}`,
                  }}
                >
                  <span
                    className="font-[family-name:var(--font-cinzel)] text-[8px] tracking-[0.15em] uppercase"
                    style={{ color: theme.accent }}
                  >
                    {theme.name}
                  </span>
                  <span className="text-[7px] text-text-disabled ml-1">
                    {theme.role}
                  </span>
                </div>

                <CourtroomCharacter
                  agentId={id}
                  pose={state.pose}
                  isSpeaking={state.isSpeaking}
                  dialogue={state.dialogue}
                />
              </motion.div>
            );
          })}
        </div>

        {/* Typing indicator */}
        <AnimatePresence>
          {isTyping && (
            <motion.div
              className="flex items-center justify-center gap-2 py-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="flex gap-1">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
              <span className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-secondary italic">
                Agent is addressing the court...
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ARBITER overlay */}
        <AnimatePresence>
          {isArbiterActive && (
            <ArbiterOverlay dialogue={activeDialogue} />
          )}
        </AnimatePresence>
      </div>

      {/* ─── BOTTOM: Assessment + Controls ─── */}
      <div className="relative z-10 flex-shrink-0 border-t border-border-default/30 p-3">
        <div className="flex items-center gap-3 mb-2">
          <h3 className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase">
            TRIBUNAL ASSESSMENT
          </h3>
          {tokenCount != null && (
            <span className="font-[family-name:var(--font-jetbrains)] text-[9px] text-text-disabled ml-auto">
              {tokenCount.toLocaleString()} tokens
            </span>
          )}
        </div>

        {/* Score bars */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          {([
            { label: "Security", score: scores.security, color: "#8b2020" },
            { label: "Performance", score: scores.performance, color: "#1a4a7a" },
            { label: "Maintainability", score: scores.maintainability, color: "#c9a84c" },
          ] as const).map(({ label, score, color }) => (
            <div key={label}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="font-[family-name:var(--font-cinzel)] text-[8px] text-text-secondary tracking-[0.1em]">
                  {label}
                </span>
                <span
                  className="font-[family-name:var(--font-jetbrains)] text-[10px]"
                  style={{ color }}
                >
                  {score}/10
                </span>
              </div>
              <div className="h-1 bg-bg-raised overflow-hidden">
                <motion.div
                  className="h-full"
                  style={{ background: color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${(score / 10) * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Verdict summary (shown when complete) */}
        {isComplete && (verdictText || rubricVerdict) && (
          <div className="mb-2 px-3 py-1.5 border border-border-default/40 bg-bg-raised/60 flex items-center gap-3">
            {rubricVerdict && (
              <span
                className="font-[family-name:var(--font-cinzel)] text-[9px] tracking-[0.2em] uppercase px-2 py-0.5 border"
                style={{
                  color: rubricVerdict === "APPROVED" ? "#c9a84c" : rubricVerdict === "REJECTED" ? "#8b2020" : "#888",
                  borderColor: rubricVerdict === "APPROVED" ? "#c9a84c55" : rubricVerdict === "REJECTED" ? "#8b202055" : "#55555555",
                }}
              >
                {rubricVerdict}
              </span>
            )}
            {verdictText && (
              <span className="font-[family-name:var(--font-im-fell)] text-[10px] text-text-secondary truncate">
                {verdictText.length > 80 ? verdictText.slice(0, 80) + "…" : verdictText}
              </span>
            )}
          </div>
        )}

        {/* Controls row */}
        <div className="flex items-center justify-between">
          {/* Conflict count */}
          {conflictCount > 0 && (
            <span className="font-[family-name:var(--font-cinzel)] text-[8px] text-text-disabled tracking-[0.1em]">
              CONFLICTS: {conflictCount}
            </span>
          )}

          <div className="flex items-center gap-2 ml-auto">
            {isComplete ? (
              <>
                <button onClick={onRequestVerdict} className="btn-primary text-[10px]">
                  Request Final Verdict
                </button>
                <button onClick={onNewCase} className="btn-ghost text-[10px]">
                  New Case
                </button>
              </>
            ) : (
              <span className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-secondary italic">
                Tribunal in session...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ─── LEDGER badge (persistent, bottom-right) ─── */}
      {ledgerEntries.length > 0 && (
        <button
          onClick={() => setIsLedgerOpen(true)}
          className="fixed bottom-4 right-4 z-40 flex items-center gap-1.5 px-2.5 py-1.5 bg-bg-surface border border-border-default hover:border-gold/30 transition-colors"
        >
          <span className="font-[family-name:var(--font-cinzel)] text-[8px] text-gold tracking-[0.15em]">
            LEDGER
          </span>
          <span className="font-[family-name:var(--font-jetbrains)] text-[9px] text-text-secondary bg-bg-raised px-1.5 py-0.5">
            {ledgerEntries.length}
          </span>
        </button>
      )}

      {/* LEDGER toast */}
      <AnimatePresence>
        {currentToast && (
          <LedgerToast
            entry={currentToast}
            onDone={() => setCurrentToast(null)}
          />
        )}
      </AnimatePresence>

      {/* LEDGER slide-in panel */}
      <LedgerPanel
        isOpen={isLedgerOpen}
        onClose={() => setIsLedgerOpen(false)}
        entries={ledgerEntries}
      />
    </div>
  );
}

