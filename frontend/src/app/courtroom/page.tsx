"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { type Proceeding } from "../../../components/proceedings/ProceedingsFeed";
import VerdictModal, { type ConflictCluster } from "../../../components/verdict/VerdictModal";
import CourtroomStage from "../../../components/courtroom/CourtroomStage";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const MESSAGE_DELAY_BASE = 800;

/** Playback speed options */
const SPEED_OPTIONS = [1, 2, 3] as const;
type SpeedMultiplier = (typeof SPEED_OPTIONS)[number];

/** Dynamic speaking duration: time for typewriter to finish + reading buffer.
 *  Click-to-advance (VN pattern) lets users skip this, so we keep it tight. */
function getSpeakingDuration(text: string): number {
  const charCount = text.length;
  // 40ms per char typewriter + 900ms reading buffer, floor 2.2s for short messages
  return Math.max(2200, charCount * 40 + 900);
}

const AGENT_ROLES: Record<string, string> = {
  LEDGER: "Clerk",
  AEGIS: "Prosecutor",
  AXIOM: "Defense",
  METRIC: "Expert Witness",
  ARBITER: "Judge",
};


const PHASE_ORDER = ["investigation", "conflict_detection", "cross_examination", "verdict", "complete"];
const PHASE_LABELS: Record<string, string> = {
  investigation: "Investigation",
  conflict_detection: "Conflict Detection",
  cross_examination: "Cross-Examination",
  verdict: "Verdict",
  complete: "Complete",
};


function CourtroomContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = searchParams.get("session_id");
  const _caseTitle = searchParams.get("title") || "Unknown Case";
  void _caseTitle; // preserved for future use

  const [proceedings, setProceedings] = useState<Proceeding[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [activeAgent, setActiveAgent] = useState("");
  const [activeDialogue, setActiveDialogue] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [scores, setScores] = useState({ security: 0, performance: 0, maintainability: 0 });
  const [showVerdict, setShowVerdict] = useState(false);
  const [verdictText, setVerdictText] = useState("");
  const [verdictRecommendations, setVerdictRecommendations] = useState<string[]>([]);
  const [tokenUsage, setTokenUsage] = useState<Record<string, number> | null>(null);
  const [currentPhase, setCurrentPhase] = useState("investigation");
  const [conflictClusters, setConflictClusters] = useState<ConflictCluster[]>([]);
  const [rubricVerdict, setRubricVerdict] = useState<string | null>(null);
  const [playbackSpeed, setPlaybackSpeed] = useState<SpeedMultiplier>(1);

  const wsRef = useRef<WebSocket | null>(null);
  const messageQueueRef = useRef<Proceeding[]>([]);
  const isProcessingQueue = useRef(false);
  const mountedRef = useRef(true);
  const isCompleteRef = useRef(false);
  const wsOpenedRef = useRef(false);
  const redirectedRef = useRef(false);
  // Defer "completion" WS message until the queue has been fully drained
  const pendingCompletionRef = useRef<Record<string, unknown> | null>(null);

  // ─── VN click-to-advance state ───
  const [forceCompleteTypewriter, setForceCompleteTypewriter] = useState(false);
  const [typewriterDone, setTypewriterDone] = useState(false);
  const readingBufferTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const typewriterTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const advanceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Apply all state updates from the WS "completion" message */
  const applyCompletion = useCallback((msg: Record<string, unknown>) => {
    setIsComplete(true);
    isCompleteRef.current = true;
    setActiveAgent("");
    setIsTyping(false);
    setCurrentPhase("complete");
    const tokenUsage = msg.token_usage as Record<string, number> | undefined;
    const conflictClusters = msg.conflict_clusters as ConflictCluster[] | undefined;
    const rubricScores = msg.rubric_scores as { security?: number; performance?: number; maintainability?: number; verdict?: string } | undefined;
    if (tokenUsage) setTokenUsage(tokenUsage);
    if (conflictClusters) setConflictClusters(conflictClusters);
    if (rubricScores?.verdict) setRubricVerdict(rubricScores.verdict);
    if (rubricScores) {
      setScores({
        security: rubricScores.security ?? 5,
        performance: rubricScores.performance ?? 5,
        maintainability: rubricScores.maintainability ?? 5,
      });
    }
  }, []);

  const processQueue = useCallback(() => {
    if (isProcessingQueue.current || messageQueueRef.current.length === 0) return;
    isProcessingQueue.current = true;

    const processNext = () => {
      if (messageQueueRef.current.length === 0) {
        isProcessingQueue.current = false;
        setIsTyping(false);
        setTypewriterDone(false);
        // Queue empty — now apply any deferred completion payload
        if (pendingCompletionRef.current) {
          const pending = pendingCompletionRef.current;
          pendingCompletionRef.current = null;
          applyCompletion(pending);
        }
        return;
      }

      // Reset VN state for new message
      setForceCompleteTypewriter(false);
      setTypewriterDone(false);
      setIsTyping(true);

      setTimeout(() => {
        const msg = messageQueueRef.current.shift();
        if (!msg) {
          isProcessingQueue.current = false;
          setIsTyping(false);
          if (pendingCompletionRef.current) {
            const pending = pendingCompletionRef.current;
            pendingCompletionRef.current = null;
            applyCompletion(pending);
          }
          return;
        }

        setProceedings((prev) => [...prev, msg]);
        setActiveAgent(msg.agent);
        setActiveDialogue(msg.message);

        // Track current phase from proceeding metadata
        if (msg.phase && PHASE_ORDER.includes(msg.phase)) {
          setCurrentPhase(msg.phase);
        }

        if (msg.tag === "Final Verdict") {
          setVerdictText(msg.message);
          if (msg.rubric_scores) {
            setScores({
              security: msg.rubric_scores.security ?? 5,
              performance: msg.rubric_scores.performance ?? 5,
              maintainability: msg.rubric_scores.maintainability ?? 5,
            });
            if (msg.rubric_scores.verdict) setRubricVerdict(msg.rubric_scores.verdict);
          }
        }

        // Phase 1: typewriter runs at 35ms/char, divided by speed
        const typewriterDuration = (msg.message.length * 35) / playbackSpeed;
        typewriterTimeoutRef.current = setTimeout(() => {
          setTypewriterDone(true);
          // Phase 2: reading buffer, divided by speed
          const readingDuration = (getSpeakingDuration(msg.message) - msg.message.length * 35) / playbackSpeed;
          readingBufferTimeoutRef.current = setTimeout(() => {
            advanceTimeoutRef.current = setTimeout(() => {
              setActiveAgent((current) => (current === msg.agent ? "" : current));
              setActiveDialogue((current) => current === msg.message ? null : current);
              setIsTyping(false);
              setTypewriterDone(false);
              setTimeout(processNext, 400 / playbackSpeed);
            }, 400 / playbackSpeed);
          }, Math.max(0, readingDuration));
        }, typewriterDuration);
      }, MESSAGE_DELAY_BASE / playbackSpeed);
    };

    processNext();
  }, [applyCompletion, playbackSpeed]);

  /** VN click-to-advance: 1st click skips typewriter, 2nd click advances to next message */
  const handleAdvance = useCallback(() => {
    // Nothing to advance if no active speaker or trial is done
    if (!activeDialogue || isComplete) return;

    if (!typewriterDone) {
      // First click: skip typewriter, reveal all text instantly
      setForceCompleteTypewriter(true);
      setTypewriterDone(true);
      // Clear the typewriter timeout (Phase 1)
      if (typewriterTimeoutRef.current) {
        clearTimeout(typewriterTimeoutRef.current);
        typewriterTimeoutRef.current = null;
      }
      // Also clear any reading buffer that hasn't started yet
      if (readingBufferTimeoutRef.current) {
        clearTimeout(readingBufferTimeoutRef.current);
        readingBufferTimeoutRef.current = null;
      }
      // Start a fresh short reading buffer from now
      readingBufferTimeoutRef.current = setTimeout(() => {
        if (advanceTimeoutRef.current) clearTimeout(advanceTimeoutRef.current);
        setActiveAgent("");
        setActiveDialogue(null);
        setIsTyping(false);
        setTypewriterDone(false);
        // Reset processing flag before re-triggering queue
        isProcessingQueue.current = false;
        // Re-trigger queue processing for next message
        setTimeout(() => processQueue(), 400 / playbackSpeed);
      }, 900 / playbackSpeed);
    } else {
      // Second click: skip reading buffer, advance immediately
      if (readingBufferTimeoutRef.current) {
        clearTimeout(readingBufferTimeoutRef.current);
        readingBufferTimeoutRef.current = null;
      }
      if (advanceTimeoutRef.current) {
        clearTimeout(advanceTimeoutRef.current);
        advanceTimeoutRef.current = null;
      }
      setActiveAgent("");
      setActiveDialogue(null);
      setIsTyping(false);
      setTypewriterDone(false);
      setForceCompleteTypewriter(false);
      // Reset processing flag before re-triggering queue
      isProcessingQueue.current = false;
      setTimeout(() => processQueue(), 400 / playbackSpeed);
    }
  }, [typewriterDone, activeDialogue, isComplete, processQueue, playbackSpeed]);

  /** Cycle through speed options: 1x → 2x → 3x → 1x */
  const cycleSpeed = useCallback(() => {
    setPlaybackSpeed((prev) => {
      const idx = SPEED_OPTIONS.indexOf(prev);
      return SPEED_OPTIONS[(idx + 1) % SPEED_OPTIONS.length];
    });
  }, []);

  const connectWebSocket = useCallback(() => {
    if (!sessionId || !mountedRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/ws/trial/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      wsOpenedRef.current = true;
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "connection") return;

        if (msg.type === "proceeding" && msg.data) {
          messageQueueRef.current.push(msg.data);
          processQueue();
        } else if (msg.type === "completion") {
          // Defer completion state updates until the message queue has
          // fully drained, so agents finish displaying before the UI
          // transitions to the "complete" / verdict state.
          if (messageQueueRef.current.length > 0 || isProcessingQueue.current) {
            pendingCompletionRef.current = msg as Record<string, unknown>;
          } else {
            applyCompletion(msg as Record<string, unknown>);
          }
        } else if (msg.type === "error") {
          if (redirectedRef.current) return;
          redirectedRef.current = true;
          console.warn("Tribunal session error:", msg.message);
          router.push("/file");
        }
      } catch {
        console.error("WS parse error");
      }
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setIsConnected(false);
      wsRef.current = null;

      if (redirectedRef.current || wsOpenedRef.current || isCompleteRef.current) return;

      redirectedRef.current = true;
      router.push("/file");
    };
  }, [sessionId, processQueue, router, applyCompletion]);

  useEffect(() => {
    mountedRef.current = true;

    if (!sessionId) {
      router.push("/file");
      return;
    }

    connectWebSocket();

    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
    };
  }, [sessionId, connectWebSocket, router]);

  // Agent status helpers (kept for VerdictModal conflict display)
  const _getAgentStatuses = useCallback(() => {
    const spokenAgents = new Set(proceedings.map((p) => p.agent));
    return Object.keys(AGENT_ROLES).map((name) => {
      const isSpeaking = name === activeAgent;
      const hasSpoken = spokenAgents.has(name);
      return {
        name,
        role: AGENT_ROLES[name],
        status: isSpeaking ? "Speaking" : hasSpoken ? "On Standby" : "Awaiting",
        isActive: isSpeaking,
      };
    });
  }, [proceedings, activeAgent]);
  void _getAgentStatuses;

  const _questItems = [
    { text: "Case filed & parsed (LEDGER)", completed: proceedings.some((p) => p.agent === "LEDGER") },
    { text: "Parallel investigation (AEGIS, AXIOM, METRIC)", completed: currentPhase !== "investigation" && proceedings.some((p) => p.agent === "AEGIS") },
    { text: "Conflict detection", completed: ["cross_examination", "verdict", "complete"].includes(currentPhase) },
    { text: "Cross-examination (if conflicts)", completed: ["verdict", "complete"].includes(currentPhase) },
    { text: "Per-item verdict (ARBITER)", completed: isComplete },
  ];
  void _questItems;

  const _currentObjective = isComplete
    ? "Verdict rendered. The tribunal has spoken."
    : !isConnected
    ? "Awaiting tribunal assembly..."
    : proceedings.length === 0
    ? "Summoning the court officers..."
    : `Phase: ${PHASE_LABELS[currentPhase] || currentPhase}`;
  void _currentObjective;

  const handleShowVerdict = () => {
    redirectedRef.current = true;
    const recs = verdictText
      .split("\n")
      .filter((l) => l.trim().startsWith("-") || l.trim().startsWith("*"))
      .map((l) => l.replace(/^[-*]\s*/, ""));
    setVerdictRecommendations(
      recs.length > 0 ? recs : ["Review identified security concerns", "Address performance bottlenecks"]
    );
    setShowVerdict(true);
  };

  const handleNewCase = () => {
    setShowVerdict(false);
    redirectedRef.current = true;
    router.push("/file");
  };

  return (
    <main className="min-h-screen bg-bg-primary">
      <CourtroomStage
        activeSpeaker={activeAgent}
        activeDialogue={activeDialogue}
        currentPhase={currentPhase}
        isTyping={isTyping}
        forceCompleteTypewriter={forceCompleteTypewriter}
        typewriterDone={typewriterDone}
        proceedings={proceedings}
        scores={scores}
        isComplete={isComplete}
        verdictText={verdictText}
        rubricVerdict={rubricVerdict}
        conflictCount={conflictClusters.length}
        onRequestVerdict={handleShowVerdict}
        onNewCase={handleNewCase}
        onAdvance={handleAdvance}
        tokenCount={tokenUsage?.total_tokens}
        playbackSpeed={playbackSpeed}
        onCycleSpeed={cycleSpeed}
      />

      {/* Verdict Modal */}
      <VerdictModal
        isOpen={showVerdict}
        onClose={() => setShowVerdict(false)}
        onNewCase={handleNewCase}
        verdict={rubricVerdict || "PENDING"}
        scores={scores}
        recommendations={verdictRecommendations}
        conflictClusters={conflictClusters}
      />
    </main>
  );
}

export default function CourtroomPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center text-text-secondary font-[family-name:var(--font-im-fell)]">
          Entering the courtroom...
        </div>
      }
    >
      <CourtroomContent />
    </Suspense>
  );
}
