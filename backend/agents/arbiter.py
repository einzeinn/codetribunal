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

        # Compute deterministic verdict from scores (no LLM guessing)
        verdict = self._compute_verdict(rubric)

        # Build per-finding evidence block for the LLM
        per_finding_evidence = self._build_per_finding_evidence(
            all_findings, conflict_clusters
        )

        prompt = (
            "All evidence has been presented. Issue your FINAL VERDICT.\n\n"
            f"Full transcript:\n{transcript}\n\n"
            "═══════════════════════════════════════════\n"
            "PER-FINDING EVIDENCE (rule on EACH individually):\n"
            f"{per_finding_evidence}\n"
            "═══════════════════════════════════════════\n\n"
            "CRITICAL LINE RANGE RULE: For each finding, you MUST copy the line range "
            "EXACTLY as shown above (e.g. 'lines 15-18'). Do NOT invent, swap, or combine "
            "line numbers from different findings. If the evidence says 'lines 15-18', "
            "write 'lines 15-18' — never 'lines 18-15' or any other range.\n\n"
            f"TRIBUNAL ASSESSMENT (deterministic rubric scores — you MUST cite these exactly):\n"
            f"  Security: {rubric['security']}/10 "
            f"({rubric['security_detail']})\n"
            f"  Performance: {rubric['performance']}/10 "
            f"({rubric['performance_detail']})\n"
            f"  Maintainability: {rubric['maintainability']}/10 "
            f"({rubric['maintainability_detail']})\n\n"
            f"FINAL RULING (already determined — you MUST use this exact verdict): {verdict}\n\n"
            "INSTRUCTIONS FOR EACH FINDING:\n"
            "- State the finding ID and line range\n"
            "- Status: CONFIRMED, DISMISSED, or DISPUTED\n"
            "- Reference the SPECIFIC tool evidence or cross-exam argument that determined your ruling\n"
            "- If the finding was uncontested, cite why it stands alone\n"
            "- If it was cross-examined, cite what the opposing agent said and why one side won\n"
            "- Do NOT use the same phrasing for different findings — each ruling must reflect its unique evidence\n\n"
            "REBUTTAL EVALUATION RULES (FOLLOW STRICTLY):\n"
            "- If an opposing agent provided a specific, evidence-backed rebuttal (citing AST analysis, "
            "tool output, or code patterns) with confidence >= 0.8, and the original agent did NOT "
            "provide a concrete counter-argument, you MUST rule DISMISSED for the original finding\n"
            "- 'Its mere presence suggests potential future misuse' is NOT a valid counter to "
            "'AST proves this function is never called' — rule DISMISSED in such cases\n"
            "- If the opposing agent withdrew, rule CONFIRMED for the original finding\n"
            "- If both sides maintained high confidence but with different evidence, rule DISPUTED\n"
            "- A rebuttal that cites specific code evidence (function names, line numbers, AST parse results) "
            "is STRONGER than vague assertions about 'potential future misuse'\n"
            "- Findings marked ***STRONG REBUTTAL*** should almost always be DISMISSED unless the "
            "original agent provided an equally strong counter\n\n"
            "Speak with judicial authority. No bullet points, no emoji, no markdown. "
            "Keep each item ruling to 2-3 sentences. End with the final ruling."
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

    def _build_per_finding_evidence(
        self,
        findings: List[AgentFinding],
        clusters: List[ConflictCluster],
    ) -> str:
        """
        Build a per-finding evidence block with cross-exam outcomes.
        Gives the LLM specific context for each finding so it can produce
        differentiated reasoning instead of template text.
        """
        # Map findings to their cluster (if any)
        finding_cluster: dict = {}
        for c in clusters:
            for f in c.findings:
                finding_cluster[f.finding_id] = c

        parts = []
        for f in findings[:15]:  # Cap to avoid token explosion
            cluster = finding_cluster.get(f.finding_id)
            withdrawn_tag = " [WITHDRAWN in cross-exam]" if f.withdrawn else ""

            # Validate line range — fix reversed or invalid ranges
            ls, le = f.line_start, f.line_end
            if ls > le:
                ls, le = le, ls  # swap if reversed
            if ls == le:
                line_display = f"line {ls}"
            else:
                line_display = f"lines {ls}-{le}"

            evidence_block = f"  {f.finding_id} ({line_display})\n"
            evidence_block += f"    Agent: {f.agent} | Category: {f.category} | Severity: {f.severity}\n"
            evidence_block += f"    Claim: {f.claim[:150]}\n"
            evidence_block += f"    Tool evidence: {f.evidence_source or 'none'}\n"
            evidence_block += f"    Confidence: {f.confidence}{withdrawn_tag}\n"

            if f.rebuttal:
                evidence_block += f"    Rebuttal from cross-exam: {f.rebuttal[:150]}\n"

            if cluster and cluster.has_conflict:
                # Show what the opposing agent said
                opponents = [
                    of for of in cluster.findings
                    if of.agent != f.agent and not of.withdrawn
                ]
                if opponents:
                    opp = opponents[0]
                    # Flag strong rebuttals (high confidence + specific evidence)
                    rebuttal_text = (opp.rebuttal or "").lower()
                    has_specific_evidence = (
                        bool(opp.evidence_source)
                        or any(kw in rebuttal_text for kw in [
                            "function", "line", "ast", "radon", "bandit",
                            "pattern", "sanitiz", "validat", "parse",
                        ])
                    )
                    is_strong = opp.confidence >= 0.8 and has_specific_evidence
                    strength_tag = " ***STRONG REBUTTAL***" if is_strong else ""
                    evidence_block += (
                        f"    Opposing argument ({opp.agent}, {opp.finding_id}): "
                        f"[{opp.severity}] {opp.claim[:100]} "
                        f"(confidence: {opp.confidence}"
                        f"{', WITHDRAWN' if opp.withdrawn else ''}){strength_tag}\n"
                    )
                    if opp.rebuttal:
                        evidence_block += f"    Opponent rebuttal: {opp.rebuttal[:150]}\n"
                state = "RESOLVED" if cluster.resolved else "UNRESOLVED"
                evidence_block += f"    Cross-exam outcome: {state} after {cluster.debate_rounds} round(s)\n"
            elif cluster and not cluster.has_conflict:
                evidence_block += "    Cross-exam: No conflict — uncontested finding\n"

            parts.append(evidence_block)

        return "\n".join(parts)

    @staticmethod
    def _compute_verdict(rubric: dict) -> str:
        """
        Deterministic verdict from rubric scores.
        No LLM guessing — the verdict is computed from the evidence.
        """
        sec = rubric["security"]
        perf = rubric["performance"]
        maint = rubric["maintainability"]
        avg = (sec + perf + maint) / 3

        if sec <= 3:
            return "REJECTED"
        elif avg < 5 or sec <= 5:
            return "APPROVED WITH CONDITIONS"
        else:
            return "APPROVED"

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
            for f in uncontested[:10]:
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
                state = "RESOLVED" if c.resolved else "UNRESOLVED"
                parts.append(f"  {c.cluster_id}: lines {c.line_start}-{c.line_end} [{state}]")
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
        # Based on cluster resolution rate, NOT finding volume.
        # Many findings = thorough analysis, not bad code.
        # Only truly unresolved contested clusters penalize the score.
        contested_unresolved = [
            c for c in clusters
            if c.has_conflict and not c.resolved
        ]
        total_clusters = len(clusters) if clusters else 1
        resolved_clusters = sum(1 for c in clusters if c.resolved)
        resolution_rate = resolved_clusters / total_clusters if total_clusters > 0 else 1.0

        # Base score from resolution rate (10 * resolution_rate)
        # Then subtract penalty for each unresolved contested cluster
        base_score = 10 * resolution_rate
        unresolved_penalty = len(contested_unresolved) * 1.0
        maintainability = max(0, min(10, round(base_score - unresolved_penalty)))
        maintainability_detail = (
            f"{resolved_clusters}/{total_clusters} clusters resolved "
            f"({resolution_rate:.0%}), "
            f"{len(contested_unresolved)} unresolved disputes"
        )

        return {
            "security": security,
            "performance": performance,
            "maintainability": maintainability,
            "security_detail": security_detail,
            "performance_detail": performance_detail,
            "maintainability_detail": maintainability_detail,
            "verdict": ArbiterAgent._compute_verdict({
                "security": security,
                "performance": performance,
                "maintainability": maintainability,
            }),
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
