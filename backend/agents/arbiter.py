"""
CodeTribunal - ARBITER Agent (The Judge)
Issues per-item verdicts with reasoning trails based on structured findings
and conflict cluster outcomes. Orchestrates the final ruling.
"""

import logging
from typing import List
from .base import (
    BaseAgent, AgentRole, ProceedingEntry, AgentFinding, ConflictCluster,
    TokenUsageLog, truncate_transcript, build_transcript, TrialPhase,
)
from ..config import settings
from ..system_prompts import ARBITER_SYSTEM_PROMPT

logger = logging.getLogger("codetribunal.agents")


class ArbiterAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.ARBITER, settings.ARBITER_MODEL, ARBITER_SYSTEM_PROMPT)

    async def process(self, context: dict) -> ProceedingEntry:
        round_num = context.get("current_round", 1)
        proceedings: List[ProceedingEntry] = context.get("proceedings", [])
        transcript = truncate_transcript(build_transcript(context))

        all_findings: List[AgentFinding] = context.get("all_findings", [])
        conflict_clusters: List[ConflictCluster] = context.get("conflict_clusters", [])

        # Build structured evidence summary for LLM verdict
        evidence_summary = self._build_evidence_summary(all_findings, conflict_clusters)

        # Issue per-item verdict
        return await self._issue_verdict(
            round_num, transcript, evidence_summary,
            all_findings, conflict_clusters, context
        )

    async def _issue_verdict(
        self, round_num: int, transcript: str,
        evidence_summary: str,
        all_findings: List[AgentFinding],
        conflict_clusters: List[ConflictCluster],
        context: dict,
    ) -> ProceedingEntry:
        # Compute deterministic rubric scores from structured findings
        rubric = self._compute_rubric_scores(all_findings, conflict_clusters)

        prompt = (
            "All evidence has been presented. Issue your FINAL VERDICT.\n\n"
            f"Evidence summary:\n{evidence_summary}\n\n"
            f"Full transcript:\n{transcript}\n\n"
            "For EACH finding in the evidence summary, rule individually:\n"
            "- State the finding ID and line range\n"
            "- Status: CONFIRMED, DISMISSED, or DISPUTED\n"
            "- Which specific tool evidence or argument won and why\n\n"
            f"TRIBUNAL ASSESSMENT (deterministic rubric scores — cite these in your ruling):\n"
            f"  Security: {rubric['security']}/10 "
            f"({rubric['security_detail']})\n"
            f"  Performance: {rubric['performance']}/10 "
            f"({rubric['performance_detail']})\n"
            f"  Maintainability: {rubric['maintainability']}/10 "
            f"({rubric['maintainability_detail']})\n\n"
            "End with: APPROVED, APPROVED WITH CONDITIONS, or REJECTED.\n"
            "Speak with judicial authority. No bullet points, no emoji, no markdown. "
            "Keep each item ruling to 2 sentences maximum. "
            "Reference specific finding IDs (e.g., AEGIS-F001) and tool evidence (e.g., bandit B608)."
        )

        content, usage = await self._call_llm(
            prompt, temperature=0.4, max_tokens=2500,
        )
        context.setdefault("token_usage", TokenUsageLog()).record(usage)

        # Build verdict proceeding with structured metadata
        primary_line = all_findings[0].line_start if all_findings else 1
        last_line = all_findings[-1].line_end if all_findings else 1

        return self._entry(
            "Final Verdict", content, round_num, 0.9,
            phase=TrialPhase.VERDICT,
            speaker=self.name,
            exhibit_ref="Verdict Scroll",
            findings=all_findings,
            line_range=[primary_line, last_line],
            rubric_scores=rubric,
        )

    def _build_evidence_summary(
        self,
        findings: List[AgentFinding],
        clusters: List[ConflictCluster],
    ) -> str:
        """
        Build a structured summary of all findings and conflict outcomes
        for the ARBITER LLM to use as evidence context.
        """
        parts = []

        # Uncontested findings
        uncontested = [
            f for f in findings
            if not any(
                f.finding_id in [cf.finding_id for cf in c.findings]
                for c in clusters if c.has_conflict
            )
        ]
        if uncontested:
            parts.append("UNCONTESTED FINDINGS:")
            for f in uncontested[:10]:  # Limit to avoid token explosion
                parts.append(
                    f"  {f.finding_id}: [{f.severity}] {f.agent} at lines "
                    f"{f.line_start}-{f.line_end} — {f.claim[:100]} "
                    f"(source: {f.evidence_source}, confidence: {f.confidence})"
                )

        # Contested clusters
        active_clusters = [c for c in clusters if c.has_conflict]
        if active_clusters:
            parts.append("\nCONTESTED ISSUES (cross-examined):")
            for c in active_clusters:
                parts.append(f"  {c.cluster_id}: lines {c.line_start}-{c.line_end}")
                for f in c.findings:
                    withdrawn_tag = " [WITHDRAWN]" if f.withdrawn else ""
                    rebuttal = f" — rebuttal: {f.rebuttal}" if f.rebuttal else ""
                    parts.append(
                        f"    {f.agent}: [{f.severity}] {f.claim[:80]} "
                        f"(confidence: {f.confidence}{withdrawn_tag}){rebuttal}"
                    )

        # Summary statistics
        confirmed = sum(1 for c in clusters if c.resolved and not c.has_conflict)
        disputed = sum(1 for c in clusters if c.resolved and c.has_conflict)
        parts.append(
            f"\nSummary: {len(findings)} total findings, "
            f"{confirmed} uncontested, {disputed} disputed after cross-examination."
        )

        return "\n".join(parts)

    @staticmethod
    def _compute_rubric_scores(
        findings: List[AgentFinding],
        clusters: List[ConflictCluster],
    ) -> dict:
        """
        Deterministic rubric scoring from structured findings.
        Scores are computed from tool evidence, not LLM guessing.

        Returns dict with security, performance, maintainability (0-10 each)
        plus human-readable detail strings.
        """
        # Only consider non-withdrawn findings for scoring
        active = [f for f in findings if not f.withdrawn]

        # ── Security Score ─────────────────────────────────────────
        # Penalise confirmed security findings by severity weight
        sec_findings = [
            f for f in active
            if f.category == "security" and f.agent in ("AEGIS", "METRIC")
        ]
        severity_weights = {"critical": 3, "high": 2, "medium": 1, "low": 0.5}
        sec_penalty = sum(severity_weights.get(f.severity, 0.5) for f in sec_findings)
        security = max(0, min(10, round(10 - sec_penalty)))
        security_detail = (
            f"{len(sec_findings)} confirmed security findings, "
            f"penalty {sec_penalty:.1f}"
        )

        # ── Performance Score ──────────────────────────────────────
        # Penalise high/medium complexity findings from METRIC (radon)
        perf_findings = [
            f for f in active
            if f.category == "complexity"
            or (f.agent == "METRIC" and f.category != "security")
        ]
        high_cc = sum(1 for f in perf_findings if f.severity == "critical")
        med_cc = sum(1 for f in perf_findings if f.severity in ("high", "medium"))
        perf_penalty = high_cc * 1.5 + med_cc * 0.5
        performance = max(0, min(10, round(10 - perf_penalty)))
        performance_detail = (
            f"{high_cc} high-complexity functions, "
            f"{med_cc} medium-complexity, penalty {perf_penalty:.1f}"
        )

        # ── Maintainability Score ──────────────────────────────────
        # Based on contested cluster outcomes + uncontested finding count
        contested = [c for c in clusters if c.has_conflict and not c.resolved]
        resolved = [c for c in clusters if c.resolved]
        maint_penalty = len(contested) * 1.5 + max(0, len(active) - 5) * 0.3
        maintainability = max(0, min(10, round(10 - maint_penalty)))
        maintainability_detail = (
            f"{len(resolved)} resolved clusters, "
            f"{len(contested)} unresolved disputes, "
            f"penalty {maint_penalty:.1f}"
        )

        return {
            "security": security,
            "performance": performance,
            "maintainability": maintainability,
            "security_detail": security_detail,
            "performance_detail": performance_detail,
            "maintainability_detail": maintainability_detail,
        }

    async def procedural_ruling(
        self, context: dict, round_num: int
    ) -> dict:
        """
        ARBITER evaluates whether cross-examination should continue.
        Returns {"action": "continue" | "conclude" | "extend", "reasoning": "..."}
        """
        import json

        clusters: List[ConflictCluster] = context.get("conflict_clusters", [])
        active = [c for c in clusters if c.has_conflict and not c.resolved]

        # Build status summary for ARBITER
        status_lines = ["Cross-examination status after round {}:".format(round_num)]
        for c in clusters:
            state = "RESOLVED" if c.resolved else (
                "DISPUTED" if c.has_conflict else "UNCONTESTED"
            )
            withdrawn_count = sum(1 for f in c.findings if f.withdrawn)
            status_lines.append(
                f"  {c.cluster_id} (lines {c.line_start}-{c.line_end}): {state}, "
                f"{c.debate_rounds}/{c.max_rounds} rounds, "
                f"{withdrawn_count} withdrawn"
            )
        status = "\n".join(status_lines)

        prompt = (
            "You are the Judge presiding over cross-examination.\n\n"
            f"{status}\n\n"
            "Decide: should the debate CONTINUE (more rounds needed to resolve conflicts), "
            "CONCLUDE (all important issues resolved or no productive debate remaining), "
            "or EXTEND (one extra round because new evidence emerged)?\n\n"
            "Respond in JSON: {\"action\": \"continue|conclude|extend\", "
            "\"reasoning\": \"one sentence\"}"
        )

        try:
            content, usage = await self._call_llm(
                prompt, temperature=0.3, max_tokens=200,
            )
            context.setdefault("token_usage", TokenUsageLog()).record(usage)

            # Parse JSON response
            # Try to extract JSON from possible markdown wrapping
            json_str = content.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[1].rsplit("```", 1)[0]

            result = json.loads(json_str)
            action = result.get("action", "continue")
            if action not in ("continue", "conclude", "extend"):
                action = "continue"
            return {
                "action": action,
                "reasoning": result.get("reasoning", "No reasoning provided"),
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"ARBITER procedural ruling parse failed: {e}, defaulting to continue")
            return {"action": "continue", "reasoning": f"Parse error: {e}"}
