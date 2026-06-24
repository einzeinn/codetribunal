"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import AgentBench from "../../../components/agents/AgentBench";
import ProceedingsFeed, { type Proceeding } from "../../../components/proceedings/ProceedingsFeed";
import QuestLog from "../../../components/ui/QuestLog";
import ScoreBar from "../../../components/ui/ScoreBar";
import VerdictModal, { type ConflictCluster } from "../../../components/verdict/VerdictModal";

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

        // Track current phase from proceeding metadata
        if (msg.phase && PHASE_ORDER.includes(msg.phase)) {
          setCurrentPhase(msg.phase);
        }

        setTimeout(() => {
          setActiveAgent((current) => (current === msg.agent ? "" : current));
        }, SPEAKING_DURATION);

        if (msg.tag === "Final Verdict") {
          const secMatch = msg.message.match(/Security\s*[:\-/]?\s*(\d+(?:\.\d+)?)/i);
          const perfMatch = msg.message.match(/Performance\s*[:\-/]?\s*(\d+(?:\.\d+)?)/i);
          const maintMatch = msg.message.match(/Maintainability\s*[:\-/]?\s*(\d+(?:\.\d+)?)/i);
          const newScores = {
            security: secMatch ? parseFloat(secMatch[1]) : 5,
            performance: perfMatch ? parseFloat(perfMatch[1]) : 5,
            maintainability: maintMatch ? parseFloat(maintMatch[1]) : 5,
          };
          setScores(newScores);
          setVerdictText(msg.message);
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
    <main className="min-h-screen flex flex-col p-4 gap-3 max-w-full overflow-x-hidden bg-bg-primary">
      {/* Header — fixed 48px */}
      <header className="text-center py-3 border-b border-[#2a2a2a] flex-shrink-0">
        <h1 className="font-[family-name:var(--font-cinzel)] text-[13px] text-gold tracking-[4px]">CODE TRIBUNAL</h1>
        <p className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-secondary mt-0.5 italic truncate">{caseTitle}</p>
        {isConnected && !isComplete && (
          <p className="font-[family-name:var(--font-im-fell)] text-[10px] text-[#4a8a4a] mt-0.5 flex items-center justify-center gap-1">
            <span className="inline-block w-1.5 h-1.5 bg-[#4a8a4a] rounded-full animate-pulse-live" />
            Live — {PHASE_LABELS[currentPhase] || currentPhase}
          </p>
        )}
        {/* Phase progress bar */}
        <div className="mt-2 max-w-[400px] mx-auto">
          <PhaseProgressBar currentPhase={currentPhase} />
        </div>
      </header>

      {/* Agent Bench — 72px */}
      <div className="flex-shrink-0">
        <AgentBench agents={getAgentStatuses()} />
      </div>

      {/* Diamond divider */}
      <DiamondDivider />

      {/* Courtroom Floor layout */}
      <div className="flex-1 flex flex-col md:flex-row gap-4 min-h-0 overflow-hidden">
        {/* Left: Prosecution (AEGIS) + Proceedings feed */}
        <div className="flex-[7] flex flex-col min-w-0 overflow-hidden">
          {/* Courtroom floor grid */}
          <div className="courtroom-floor flex-1 min-h-0">
            {/* Judge bench (ARBITER) */}
            <div className="judge-bench border-b border-[#2a2a2a] pb-2 mb-2">
              <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-gold tracking-[0.2em] uppercase">
                ARBITER — Judge
              </span>
            </div>

            {/* Prosecution table (AEGIS) */}
            <div className="prosecution-table border-r border-[#2a2a2a] pr-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-[#8b2020]" />
                <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-[#8b2020] tracking-[0.15em] uppercase">
                  AEGIS — Prosecutor
                </span>
              </div>
              <p className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-disabled italic">
                Security vulnerabilities &amp; accusations
              </p>
            </div>

            {/* Defense table (AXIOM) */}
            <div className="defense-table pl-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-[#2a6a2a]" />
                <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-[#2a6a2a] tracking-[0.15em] uppercase">
                  AXIOM — Defense
                </span>
              </div>
              <p className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-disabled italic">
                Validation &amp; counter-evidence
              </p>
            </div>

            {/* Exhibit board — proceedings feed spans full width */}
            <div className="exhibit-board min-h-0 overflow-hidden flex flex-col">
              <ProceedingsFeed
                proceedings={proceedings}
                isTyping={isTyping}
                isConnected={isConnected}
                currentPhase={currentPhase}
              />
            </div>
          </div>
        </div>

        {/* Right: Quest Log (220px fixed) */}
        <div className="w-full md:w-[220px] md:flex-shrink-0 flex flex-col">
          <QuestLog items={questItems} currentObjective={currentObjective} />

          {/* Conflict clusters summary (if any) */}
          {conflictClusters.length > 0 && (
            <div className="mt-4 pl-4 border-l border-[#2a2a2a]">
              <h4 className="font-[family-name:var(--font-cinzel)] text-[8px] text-text-secondary tracking-[0.15em] uppercase mb-2">
                CONFLICTS ({conflictClusters.length})
              </h4>
              {conflictClusters.slice(0, 5).map((c: ConflictCluster, i: number) => (
                <div key={c.cluster_id || i} className="mb-2 text-[11px]">
                  <span className="font-[family-name:var(--font-jetbrains)] text-gold text-[9px]">
                    L{c.line_start}-{c.line_end}
                  </span>
                  <span className={`ml-1 ${
                    c.resolved ? "text-[#2a6a2a]" : "text-[#8b2020]"
                  }`}>
                    {c.resolved ? "Resolved" : "Contested"}
                  </span>
                  <span className="text-text-disabled ml-1">
                    ({c.findings?.length || 0} agents)
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Diamond divider */}
      <DiamondDivider />

      {/* Tribunal Assessment — 80px */}
      <div className="flex-shrink-0 py-4 border-t border-[#2a2a2a]">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase">
            TRIBUNAL ASSESSMENT
          </h3>
          {tokenUsage && (
            <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-disabled ml-auto">
              {tokenUsage.total_tokens?.toLocaleString()} tokens
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <ScoreBar label="Security" score={scores.security} color="#8b2020" />
          <ScoreBar label="Performance" score={scores.performance} color="#1a4a7a" />
          <ScoreBar label="Maintainability" score={scores.maintainability} color="#c9a84c" />
        </div>

        <div className="flex justify-end">
          {isComplete ? (
            <button onClick={handleShowVerdict} className="btn-primary">
              Request Final Verdict
            </button>
          ) : (
            <span className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-secondary italic">
              {isConnected ? `Tribunal in session — ${PHASE_LABELS[currentPhase] || currentPhase}...` : "Awaiting connection..."}
            </span>
          )}
        </div>
      </div>

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
