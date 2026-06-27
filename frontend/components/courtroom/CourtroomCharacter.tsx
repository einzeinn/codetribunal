"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AGENTS, spritePath, type AgentId, type Pose } from "../../lib/courtroom-theme";

interface CourtroomCharacterProps {
  agentId: AgentId;
  pose: Pose;
  isSpeaking: boolean;
  dialogue: string | null;
}

export default function CourtroomCharacter({
  agentId,
  pose,
  isSpeaking,
  dialogue,
}: CourtroomCharacterProps) {
  const theme = AGENTS[agentId];
  const src = spritePath(agentId, pose);

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
            scale: isSpeaking ? 1.05 : 1,
          }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          draggable={false}
        />
      </AnimatePresence>

      {/* Dialogue box — overlaid on the sprite from chest to bottom */}
      <AnimatePresence>
        {dialogue && (
          <motion.div
            className="absolute left-0 right-0 bottom-0 z-10"
            style={{ top: "45%" }}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
          >
            <div
              className="h-full flex flex-col p-3 overflow-y-auto"
              style={{
                background: `rgba(${theme.accentRgb}, 0.12)`,
                borderColor: theme.accent,
                borderWidth: 1,
                borderStyle: "solid",
              }}
            >
              {/* Header */}
              <div className="flex items-center gap-1.5 mb-1.5 flex-shrink-0">
                <span
                  className="font-[family-name:var(--font-cinzel)] text-[9px] tracking-[0.15em] uppercase"
                  style={{ color: theme.accent }}
                >
                  {theme.name}
                </span>
                <span className="text-[8px] text-text-disabled tracking-[0.1em]">
                  — {theme.role}
                </span>
              </div>

              {/* Dialogue text */}
              <p className="text-[12px] text-text-primary leading-[1.6] font-[family-name:var(--font-im-fell)] italic">
                {dialogue}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
