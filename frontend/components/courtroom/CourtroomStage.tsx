"use client";

import { useState, useRef } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import CourtroomCharacter from "./CourtroomCharacter";
import { AGENTS, toAgentId, spritePath, type AgentId } from "../../lib/courtroom-theme";
import { type Proceeding } from "../proceedings/ProceedingsFeed";

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
  /** Force typewriter to skip to end (VN click-to-skip) */
  forceCompleteTypewriter?: boolean;
  /** Whether typewriter has finished for the current message */
  typewriterDone?: boolean;
  /** All proceedings for replay after verdict */
  proceedings?: Proceeding[];
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
  /** Callback: user clicked to advance (VN skip/advance) */
  onAdvance?: () => void;
  /** Token usage for display */
  tokenCount?: number;
  /** Current playback speed multiplier */
  playbackSpeed?: number;
  /** Callback to cycle through speed options */
  onCycleSpeed?: () => void;
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
              <span className="font-[family-name:var(--font-cinzel)] text-[12px] text-gold tracking-[0.2em] uppercase">
                LEDGER — Session Log
              </span>
              <button onClick={onClose} className="text-text-secondary hover:text-text-primary text-sm">
                ✕
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(100vh-60px)]">
              {entries.length === 0 ? (
                <p className="text-[14px] text-text-disabled italic">
                  No entries recorded yet.
                </p>
              ) : (
                <div className="space-y-3">
                  {[...entries].reverse().map((e) => (
                    <div key={e.id} className="border-b border-border-default/50 pb-2">
                      <p className="text-[13px] text-text-primary leading-[1.6]">
                        {e.text}
                      </p>
                      <span className="text-[11px] text-text-disabled font-[family-name:var(--font-jetbrains)]">
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

/* ─── Proceedings Replay Panel ─── */

function ProceedingsReplayPanel({
  isOpen,
  onClose,
  proceedings,
}: {
  isOpen: boolean;
  onClose: () => void;
  proceedings: Proceeding[];
}) {
  const agentColors: Record<string, string> = {
    LEDGER: AGENTS.ledger.accent,
    AEGIS: AGENTS.aegis.accent,
    AXIOM: AGENTS.axiom.accent,
    METRIC: AGENTS.metric.accent,
    ARBITER: AGENTS.arbiter.accent,
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-40 bg-black/70"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={(e) => { e.stopPropagation(); onClose(); }}
          />
          {/* Panel */}
          <motion.div
            className="fixed top-0 left-0 bottom-0 z-50 w-full md:w-[680px] bg-bg-surface border-r border-border-default overflow-hidden flex flex-col"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "tween", duration: 0.3 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="p-4 border-b border-border-default flex items-center justify-between flex-shrink-0">
              <span className="font-[family-name:var(--font-cinzel)] text-[14px] text-gold tracking-[0.2em] uppercase">
                Trial Proceedings
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); onClose(); }}
                className="text-text-secondary hover:text-text-primary text-lg px-2"
              >
                ✕
              </button>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {proceedings.length === 0 ? (
                <p className="text-[14px] text-text-disabled italic text-center py-8">
                  No proceedings recorded.
                </p>
              ) : (
                proceedings.map((p, i) => (
                  <div
                    key={`${p.agent}-${p.round_number}-${i}`}
                    className="border border-border-default/50 p-3"
                    style={{
                      background: "linear-gradient(180deg, rgba(8,8,10,0.6), rgba(8,8,10,0.8))",
                    }}
                  >
                    {/* Header row */}
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className="font-[family-name:var(--font-cinzel)] text-[11px] tracking-[0.15em] uppercase px-2 py-0.5 border"
                        style={{
                          color: agentColors[p.agent] || "#888",
                          borderColor: `${agentColors[p.agent] || "#555"}55`,
                        }}
                      >
                        {p.agent}
                      </span>
                      {p.tag && (
                        <span className="text-[10px] text-text-disabled">{p.tag}</span>
                      )}
                      {p.phase && (
                        <span className="text-[10px] text-text-disabled ml-auto">
                          {p.phase.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>

                    {/* Message content */}
                    <p
                      className="text-[13px] leading-[1.7] whitespace-pre-wrap"
                      style={{ color: "#e8e5dc" }}
                    >
                      {p.message}
                    </p>

                    {/* Findings if any */}
                    {p.findings && p.findings.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-border-default/30">
                        <span className="text-[9px] text-gold/70 tracking-[0.1em] uppercase">
                          Findings ({p.findings.length})
                        </span>
                        <div className="mt-1 space-y-1">
                          {p.findings.map((f) => (
                            <div key={f.finding_id} className="text-[11px] text-text-secondary pl-2 border-l border-border-default/30">
                              <span className="text-text-disabled">{f.finding_id}:</span> {f.claim.slice(0, 100)}
                              {f.claim.length > 100 && "…"}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))
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
  forceComplete,
}: {
  dialogue: string | null;
  forceComplete?: boolean;
}) {
  return (
    <motion.div
      className="absolute inset-0 z-30 flex flex-col items-center justify-center"
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: -20, opacity: 0 }}
      transition={{ type: "spring", bounce: 0.3, duration: 0.5 }}
    >
      {/* Dimmed backdrop — clicks bubble up to stage for VN advance */}
      <div className="absolute inset-0 bg-black/70" />

      {/* ARBITER character — full screen height, dominates the stage */}
      <div className="relative z-10 flex flex-col items-center justify-end h-full max-h-[80vh] w-[380px] md:w-[520px]">
        <CourtroomCharacter
          agentId="arbiter"
          pose="active"
          isSpeaking
          dialogue={dialogue}
          forceComplete={forceComplete}
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
  forceCompleteTypewriter = false,
  typewriterDone = false,
  proceedings = [],
  scores,
  isComplete,
  verdictText,
  rubricVerdict,
  conflictCount = 0,
  onRequestVerdict,
  onNewCase,
  onAdvance,
  tokenCount,
  playbackSpeed = 1,
  onCycleSpeed,
}: CourtroomStageProps) {
  const [isLedgerOpen, setIsLedgerOpen] = useState(false);
  const [isReviewOpen, setIsReviewOpen] = useState(false);

  // Track significant events for LEDGER
  // Session tracking for LEDGER (simple count, no detailed entries)
  const [sessionCount] = useState(1);
  const sessionStartTime = useRef(new Date().toLocaleTimeString());

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
    <div
      className="relative w-full h-full min-h-screen flex flex-col overflow-hidden cursor-pointer"
      onClick={onAdvance}
      role="presentation"
    >
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
        <div className="flex items-center justify-between px-4">
          {/* Left: Speed control button */}
          <button
            onClick={(e) => { e.stopPropagation(); onCycleSpeed?.(); }}
            className="font-[family-name:var(--font-jetbrains)] text-[11px] text-gold/80 hover:text-gold px-2 py-1 border border-gold/30 hover:border-gold transition-colors"
          >
            {playbackSpeed}x
          </button>

          {/* Center: Title */}
          <div className="flex-1">
            <h1 className="font-[family-name:var(--font-cinzel)] text-[16px] text-gold tracking-[4px]">
              CODE TRIBUNAL
            </h1>
          </div>

          {/* Right: spacer for balance */}
          <div className="w-[40px]" />
        </div>

        {!isComplete && (
          <p className="text-[12px] text-[#4a8a4a] mt-0.5 flex items-center justify-center gap-1.5">
            <span className="inline-block w-2 h-2 bg-[#4a8a4a] rounded-full animate-pulse-live" />
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
                transition={{ duration: 0.4, ease: "easeOut" }}
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
                    className="font-[family-name:var(--font-cinzel)] text-[10px] tracking-[0.15em] uppercase"
                    style={{ color: theme.accent }}
                  >
                    {theme.name}
                  </span>
                  <span className="text-[9px] text-text-disabled ml-1">
                    {theme.role}
                  </span>
                </div>

                <CourtroomCharacter
                  agentId={id}
                  pose={state.pose}
                  isSpeaking={state.isSpeaking}
                  dialogue={state.dialogue}
                  forceComplete={state.isSpeaking ? forceCompleteTypewriter : false}
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
              <span className="text-[13px] text-text-secondary">
                Agent is addressing the court...
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ARBITER overlay */}
        <AnimatePresence>
          {isArbiterActive && (
            <ArbiterOverlay dialogue={activeDialogue} forceComplete={forceCompleteTypewriter} />
          )}
        </AnimatePresence>

        {/* Click-to-advance hint — appears when typewriter is done */}
        <AnimatePresence>
          {activeDialogue && typewriterDone && !isComplete && (
            <motion.div
              className="absolute bottom-4 left-1/2 z-20 flex items-center gap-1.5"
              style={{ x: "-50%" }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3, delay: 0.2 }}
            >
              <span className="text-gold text-[14px] animate-bounce">▼</span>
              <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-gold/70 tracking-[0.15em] uppercase">
                click to continue
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ─── BOTTOM: Assessment + Controls ─── */}
      <div className="relative z-10 flex-shrink-0 border-t border-border-default/30 p-3">
        <div className="flex items-center gap-3 mb-2">
          <h3 className="font-[family-name:var(--font-cinzel)] text-[11px] text-text-secondary tracking-[0.2em] uppercase">
            TRIBUNAL ASSESSMENT
          </h3>
          {tokenCount != null && (
            <span className="font-[family-name:var(--font-jetbrains)] text-[11px] text-text-disabled ml-auto">
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
                <span className="font-[family-name:var(--font-cinzel)] text-[10px] text-text-secondary tracking-[0.1em]">
                  {label}
                </span>
                <span
                  className="font-[family-name:var(--font-jetbrains)] text-[12px]"
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
                className="font-[family-name:var(--font-cinzel)] text-[11px] tracking-[0.2em] uppercase px-2 py-0.5 border"
                style={{
                  color: rubricVerdict === "APPROVED" ? "#c9a84c" : rubricVerdict === "REJECTED" ? "#8b2020" : "#888",
                  borderColor: rubricVerdict === "APPROVED" ? "#c9a84c55" : rubricVerdict === "REJECTED" ? "#8b202055" : "#55555555",
                }}
              >
                {rubricVerdict}
              </span>
            )}
            {verdictText && (
              <span className="text-[12px] text-text-secondary truncate">
                {verdictText.length > 80 ? verdictText.slice(0, 80) + "…" : verdictText}
              </span>
            )}
          </div>
        )}

        {/* Controls row */}
        <div className="flex items-center justify-between">
          {/* Conflict count */}
          {conflictCount > 0 && (
            <span className="font-[family-name:var(--font-cinzel)] text-[10px] text-text-disabled tracking-[0.1em]">
              CONFLICTS: {conflictCount}
            </span>
          )}

          <div className="flex items-center gap-2 ml-auto">
            {isComplete ? (
              <>
                <button
                  onClick={(e) => { e.stopPropagation(); setIsReviewOpen(true); }}
                  className="btn-ghost text-[10px]"
                >
                  Review Proceedings
                </button>
                <button onClick={onRequestVerdict} className="btn-primary text-[10px]">
                  Request Final Verdict
                </button>
                <button onClick={onNewCase} className="btn-ghost text-[10px]">
                  New Case
                </button>
              </>
            ) : (
              <span className="text-[13px] text-text-secondary">
                Tribunal in session...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ─── LEDGER character (persistent, bottom-right) ─── */}
      <div className="fixed bottom-2 right-2 z-40 flex items-end gap-2 group">
        {/* Dialogue text box to the LEFT of the sprite */}
        {activeSpeaker && toAgentId(activeSpeaker) === "ledger" && activeDialogue && (
          <motion.div
            className="max-w-[200px] md:max-w-[240px] p-2.5 mb-6"
            style={{
              background: "linear-gradient(180deg, rgba(8,8,10,0.80), rgba(8,8,10,0.93))",
              backdropFilter: "blur(6px)",
              WebkitBackdropFilter: "blur(6px)",
              border: `1px solid ${AGENTS.ledger.accent}`,
              boxShadow: `0 0 16px rgba(${AGENTS.ledger.accentRgb}, 0.12)`,
            }}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <span
                className="font-[family-name:var(--font-cinzel)] text-[9px] tracking-[0.15em] uppercase"
                style={{ color: AGENTS.ledger.accent }}
              >
                LEDGER
              </span>
              <span className="text-[9px] text-[#777] tracking-[0.1em]">
                — {AGENTS.ledger.role}
              </span>
            </div>
            <p
              className="text-[12px] leading-[1.65]"
              style={{ color: "#f0ede4", fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" }}
            >
              {activeDialogue.length > 120 ? activeDialogue.slice(0, 120) + "…" : activeDialogue}
            </p>
          </motion.div>
        )}

        {/* LEDGER sprite (click opens session info panel) */}
        <button
          onClick={(e) => { e.stopPropagation(); setIsLedgerOpen(true); }}
          className="flex flex-col items-center group/sprite"
        >
          <Image
            src={spritePath("ledger", isComplete ? "writing" : "neutral")}
            alt="LEDGER — Clerk"
            width={90}
            height={135}
            className="w-[70px] md:w-[90px] h-auto select-none transition-all duration-300 group-hover/sprite:scale-105"
            style={{
              filter: `drop-shadow(0 0 ${isComplete ? "8px " + AGENTS.ledger.accent : "3px rgba(0,0,0,0.5)"})`,
            }}
            draggable={false}
          />
          {/* Session count badge */}
          <div className="flex items-center gap-1 px-2 py-0.5 bg-bg-surface/90 border border-border-default group-hover/sprite:border-gold/30 transition-colors">
            <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-gold tracking-[0.15em]">
              SESSION
            </span>
            <span className="font-[family-name:var(--font-jetbrains)] text-[10px] text-text-secondary bg-bg-raised px-1.5 py-0.5">
              {sessionCount}
            </span>
          </div>
        </button>
      </div>

      {/* LEDGER slide-in panel (simplified — shows session info only) */}
      <LedgerPanel
        isOpen={isLedgerOpen}
        onClose={() => setIsLedgerOpen(false)}
        entries={[
          {
            id: "session-1",
            text: `Session ${sessionCount} — started at ${sessionStartTime.current}`,
            timestamp: sessionStartTime.current,
          },
        ]}
      />

      {/* Proceedings Replay Panel */}
      <ProceedingsReplayPanel
        isOpen={isReviewOpen}
        onClose={() => setIsReviewOpen(false)}
        proceedings={proceedings}
      />
    </div>
  );
}

