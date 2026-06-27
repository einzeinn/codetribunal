"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import AgentBench from "../../../components/agents/AgentBench";
import ProceedingsFeed, { type Proceeding } from "../../../components/proceedings/ProceedingsFeed";
import QuestLog from "../../../components/ui/QuestLog";
import ScoreBar from "../../../components/ui/ScoreBar";
import VerdictModal, { type ConflictCluster } from "../../../components/verdict/VerdictModal";
import CourtroomStage from "../../../components/courtroom/CourtroomStage";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const MESSAGE_DELAY = 800;
const SPEAKING_DURATION = 2000;

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

function DiamondDivider() {
  return (
    <div className="diamond-divider">
      <div className="diamond" />
    </div>
  );
}

function PhaseProgressBar({ currentPhase }: { currentPhase: string }) {
  const currentIndex = PHASE_ORDER.indexOf(currentPhase);
  return (
    <div className="phase-progress w-full">
      {PHASE_ORDER.slice(0, -1).map((phase, i) => (
        <div
          key={phase}
          className={`phase-step ${
            i < currentIndex ? "completed" : i === currentIndex ? "active" : ""
          }`}
          title={PHASE_LABELS[phase]}
        />
      ))}
    </div>
  );
}

function CourtroomContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = searchParams.get("session_id");
  const caseTitle = searchParams.get("title") || "Unknown Case";

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

  const wsRef = useRef<WebSocket | null>(null);
  const messageQueueRef = useRef<Proceeding[]>([]);
  const isProcessingQueue = useRef(false);
  const mountedRef = useRef(true);
  const isCompleteRef = useRef(false);
  const wsOpenedRef = useRef(false);
  const redirectedRef = useRef(false);

  const processQueue = useCallback(() => {
    if (isProcessingQueue.current || messageQueueRef.current.length === 0) return;
    isProcessingQueue.current = true;

    const processNext = () => {
      if (messageQueueRef.current.length === 0) {
        isProcessingQueue.current = false;
        setIsTyping(false);
        return;
      }

      setIsTyping(true);

      setTimeout(() => {
        const msg = messageQueueRef.current.shift();
        if (!msg) {
          isProcessingQueue.current = false;
          setIsTyping(false);
          return;
        }

        setProceedings((prev) => [...prev, msg]);
        setActiveAgent(msg.agent);
        setActiveDialogue(msg.message);

        // Track current phase from proceeding metadata
        if (msg.phase && PHASE_ORDER.includes(msg.phase)) {
          setCurrentPhase(msg.phase);
        }

        setTimeout(() => {
          setActiveAgent((current) => (current === msg.agent ? "" : current));
          setActiveDialogue((current) => current === msg.message ? null : current);
        }, SPEAKING_DURATION);

        if (msg.tag === "Final Verdict") {
          // Use deterministic rubric_scores from backend — NOT LLM text parsing
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

        setIsTyping(false);
        setTimeout(processNext, 100);
      }, MESSAGE_DELAY);
    };

    processNext();
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
          setIsComplete(true);
          isCompleteRef.current = true;
          setActiveAgent("");
          setIsTyping(false);
          setCurrentPhase("complete");
          if (msg.token_usage) setTokenUsage(msg.token_usage);
          if (msg.conflict_clusters) setConflictClusters(msg.conflict_clusters);
          if (msg.rubric_scores?.verdict) setRubricVerdict(msg.rubric_scores.verdict);
          if (msg.rubric_scores) {
            setScores({
              security: msg.rubric_scores.security ?? 5,
              performance: msg.rubric_scores.performance ?? 5,
              maintainability: msg.rubric_scores.maintainability ?? 5,
            });
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
  }, [sessionId, processQueue, router]);

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

  const getAgentStatuses = useCallback(() => {
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

  const questItems = [
    { text: "Case filed & parsed (LEDGER)", completed: proceedings.some((p) => p.agent === "LEDGER") },
    { text: "Parallel investigation (AEGIS, AXIOM, METRIC)", completed: currentPhase !== "investigation" && proceedings.some((p) => p.agent === "AEGIS") },
    { text: "Conflict detection", completed: ["cross_examination", "verdict", "complete"].includes(currentPhase) },
    { text: "Cross-examination (if conflicts)", completed: ["verdict", "complete"].includes(currentPhase) },
    { text: "Per-item verdict (ARBITER)", completed: isComplete },
  ];

  const currentObjective = isComplete
    ? "Verdict rendered. The tribunal has spoken."
    : !isConnected
    ? "Awaiting tribunal assembly..."
    : proceedings.length === 0
    ? "Summoning the court officers..."
    : `Phase: ${PHASE_LABELS[currentPhase] || currentPhase}`;

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
        scores={scores}
        isComplete={isComplete}
        verdictText={verdictText}
        rubricVerdict={rubricVerdict}
        conflictCount={conflictClusters.length}
        onRequestVerdict={handleShowVerdict}
        onNewCase={handleNewCase}
        tokenCount={tokenUsage?.total_tokens}
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
