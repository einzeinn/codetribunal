"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AGENTS, spritePath, type AgentId, type Pose } from "../../lib/courtroom-theme";

/** Typewriter speed: ms per character reveal */
const CHAR_SPEED_MS = 35;

interface CourtroomCharacterProps {
  agentId: AgentId;
  pose: Pose;
  isSpeaking: boolean;
  dialogue: string | null;
  /** Force typewriter to instantly reveal all text (VN skip) */
  forceComplete?: boolean;
}

export default function CourtroomCharacter({
  agentId,
  pose,
  isSpeaking,
  dialogue,
  forceComplete = false,
}: CourtroomCharacterProps) {
  const theme = AGENTS[agentId];
  const src = spritePath(agentId, pose);

  // Typewriter state
  const [visibleChars, setVisibleChars] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Reset & run typewriter when dialogue changes
  useEffect(() => {
    // Clear previous interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (!dialogue) {
      setVisibleChars(0);
      return;
    }
    // Force-complete: reveal all text immediately
    if (forceComplete) {
      setVisibleChars(dialogue.length);
      return;
    }
    setVisibleChars(0);
    intervalRef.current = setInterval(() => {
      setVisibleChars((prev) => {
        if (prev >= dialogue.length) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          return prev;
        }
        return prev + 1;
      });
    }, CHAR_SPEED_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [dialogue, forceComplete]);

  // If forceComplete flips true while already typing, jump to end
  useEffect(() => {
    if (forceComplete && dialogue) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setVisibleChars(dialogue.length);
    }
  }, [forceComplete, dialogue]);

  const displayedText = dialogue ? dialogue.slice(0, visibleChars) : "";

  return (
    <div className="relative flex flex-col items-center">
      {/* Character sprite with pose swap animation */}
      <AnimatePresence mode="wait">
        <motion.img
          key={src}
          src={src}
          alt={`${theme.name} — ${theme.role}`}
          className="w-full h-auto object-contain select-none"
          style={{
            filter: isSpeaking
              ? `drop-shadow(0 0 12px ${theme.accent})`
              : "drop-shadow(0 0 4px rgba(0,0,0,0.5))",
          }}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{
            opacity: 1,
            scale: isSpeaking ? 1.04 : 1,
          }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          draggable={false}
        />
      </AnimatePresence>

      {/* Dialogue box — overlaid on the sprite from chest to bottom */}
      <AnimatePresence>
        {dialogue && (
          <motion.div
            className="absolute left-0 right-0 bottom-0 z-10"
            style={{ top: "42%" }}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.35 }}
          >
            <div
              className="h-full flex flex-col p-3 overflow-y-auto"
              style={{
                background: "linear-gradient(180deg, rgba(8,8,10,0.78), rgba(8,8,10,0.93))",
                backdropFilter: "blur(8px)",
                WebkitBackdropFilter: "blur(8px)",
                borderColor: theme.accent,
                borderWidth: 1,
                borderStyle: "solid",
                boxShadow: "0 -4px 24px rgba(0,0,0,0.45)",
              }}
            >
              {/* Header — keep Cinzel for speaker name only */}
              <div className="flex items-center gap-2 mb-1.5 flex-shrink-0">
                <span
                  className="font-[family-name:var(--font-cinzel)] text-[11px] tracking-[0.15em] uppercase"
                  style={{ color: theme.accent }}
                >
                  {theme.name}
                </span>
                <span className="text-[10px] text-[#777] tracking-[0.1em]">
                  — {theme.role}
                </span>
              </div>

              {/* Dialogue text — system sans-serif, warm-white, highly readable */}
              <p
                className="text-[14px] leading-[1.75]"
                style={{ color: "#f0ede4", fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" }}
              >
                {displayedText}
                {/* Blinking cursor while typing */}
                {visibleChars < (dialogue?.length ?? 0) && (
                  <span className="inline-block w-[2px] h-[14px] ml-0.5 align-middle animate-pulse" style={{ backgroundColor: "#f0ede4" }} />
                )}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
