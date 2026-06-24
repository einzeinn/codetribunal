"use client";

export interface ConflictCluster {
  cluster_id: string;
  line_start: number;
  line_end: number;
  findings: Array<{
    finding_id: string;
    agent: string;
    category: string;
    severity: string;
    claim: string;
    withdrawn?: boolean;
  }>;
  resolved: boolean;
  debate_rounds?: number;
}

interface VerdictModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNewCase: () => void;
  verdict: string | null;
  scores: { security: number; performance: number; maintainability: number };
  recommendations: string[];
  conflictClusters?: ConflictCluster[];
}

function DiamondDivider() {
  return (
    <div className="diamond-divider my-6">
      <div className="diamond" />
    </div>
  );
}

export default function VerdictModal({ isOpen, onClose, onNewCase, verdict, scores, recommendations, conflictClusters = [] }: VerdictModalProps) {
  if (!isOpen) return null;

  const verdictUpper = verdict?.toUpperCase() || "";
  const isRejected = verdictUpper.includes("REJECTED");
  const isApproved = verdictUpper.includes("APPROVED") && !verdictUpper.includes("CONDITIONS");

  const verdictColor = isRejected ? "text-[#8b2020]" : isApproved ? "text-[#2a6a2a]" : "text-gold";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-[#080808]/95 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Content — no card border */}
      <div className="relative max-w-[480px] w-full text-center px-12 py-16 max-h-[90vh] overflow-y-auto animate-fade-in">
        {/* FINAL RULING */}
        <h2 className="font-[family-name:var(--font-cinzel)] text-[11px] text-text-secondary tracking-[0.3em] uppercase mb-2">
          FINAL RULING
        </h2>

        {/* Verdict — Cinzel Decorative */}
        <p className={`font-[family-name:var(--font-cinzel-decorative)] text-[32px] tracking-[0.1em] ${verdictColor}`}>
          {verdict || "PENDING"}
        </p>

        <DiamondDivider />

        {/* Score summary — 3 items horizontal */}
        <div className="flex justify-center gap-8 mb-2">
          <div className="text-center">
            <p className="font-[family-name:var(--font-cinzel)] text-[24px] text-[#8b2020]">{scores.security.toFixed(0)}</p>
            <p className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary uppercase tracking-wider">Security</p>
          </div>
          <div className="text-center">
            <p className="font-[family-name:var(--font-cinzel)] text-[24px] text-[#1a4a7a]">{scores.performance.toFixed(0)}</p>
            <p className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary uppercase tracking-wider">Performance</p>
          </div>
          <div className="text-center">
            <p className="font-[family-name:var(--font-cinzel)] text-[24px] text-[#c9a84c]">{scores.maintainability.toFixed(0)}</p>
            <p className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary uppercase tracking-wider">Maintain.</p>
          </div>
        </div>

        <DiamondDivider />

        {/* Conflict clusters summary */}
        {conflictClusters.length > 0 && (
          <>
            <DiamondDivider />
            <div className="text-left max-w-[360px] mx-auto mb-6">
              <h3 className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase mb-3">
                CONFLICTS DETECTED ({conflictClusters.length})
              </h3>
              <div className="space-y-3">
                {conflictClusters.slice(0, 6).map((cluster, i) => (
                  <div key={cluster.cluster_id || i} className="border-l-2 border-[#2a2a2a] pl-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-[family-name:var(--font-jetbrains)] text-[10px] text-gold">
                        L{cluster.line_start}-{cluster.line_end}
                      </span>
                      <span className={`font-[family-name:var(--font-cinzel)] text-[8px] tracking-[0.1em] uppercase ${
                        cluster.resolved ? "text-[#2a6a2a]" : "text-[#8b2020]"
                      }`}>
                        {cluster.resolved ? "Resolved" : "Contested"}
                      </span>
                      {cluster.debate_rounds && (
                        <span className="text-[9px] text-text-disabled">
                          {cluster.debate_rounds} round{cluster.debate_rounds !== 1 ? "s" : ""}
                        </span>
                      )}
                    </div>
                    <div className="space-y-1">
                      {cluster.findings.slice(0, 3).map((f, fi) => (
                        <div key={fi} className="flex items-start gap-1.5 text-[10px]">
                          <span className={`flex-shrink-0 w-1.5 h-1.5 mt-1 rounded-full ${
                            f.withdrawn ? "bg-[#555]" : f.severity === "critical" || f.severity === "high" ? "bg-[#8b2020]" : "bg-gold"
                          }`} />
                          <span className={`leading-snug ${
                            f.withdrawn ? "text-text-disabled line-through" : "text-text-secondary"
                          }`}>
                            <span className="text-gold font-[family-name:var(--font-jetbrains)]">{f.agent}</span>
                            {f.withdrawn && <span className="text-[#8b2020] ml-1">[WITHDRAWN]</span>}
                            <br />
                            {f.claim.length > 60 ? f.claim.slice(0, 60) + "..." : f.claim}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                {conflictClusters.length > 6 && (
                  <p className="text-[10px] text-text-disabled">+{conflictClusters.length - 6} more conflicts</p>
                )}
              </div>
            </div>
          </>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className="text-left max-w-[360px] mx-auto mb-10">
            <h3 className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase mb-3">
              RECOMMENDATIONS
            </h3>
            <ul className="space-y-2">
              {recommendations.map((rec, i) => (
                <li key={i} className="font-[family-name:var(--font-im-fell)] text-[13px] text-text-primary pl-4">
                  <span className="text-gold absolute -ml-4">—</span>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* CTA */}
        <button onClick={onNewCase} className="btn-primary">
          Start New Case
        </button>
      </div>
    </div>
  );
}
