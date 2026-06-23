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
        prompt = (
            "All evidence has been presented. Issue your FINAL VERDICT.\n\n"
            f"Evidence summary:\n{evidence_summary}\n\n"
            f"Full transcript:\n{transcript}\n\n"
            "For EACH finding in the evidence summary, rule individually:\n"
            "- State the finding ID and line range\n"
            "- Status: CONFIRMED, DISMISSED, or DISPUTED\n"
            "- Which specific tool evidence or argument won and why\n\n"
            "Then provide overall scores with justification:\n"
            "- Security (0-10): cite confirmed security findings count\n"
            "- Performance (0-10): cite complexity data\n"
            "- Maintainability (0-10): cite structural issues\n\n"
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
"""
CodeTribunal - ARBITER Agent (The Judge)
Orchestrates debate flow and issues final verdict.
"""

from typing import List
from .base import (
    BaseAgent, AgentRole, ProceedingEntry,
    TokenUsageLog, truncate_transcript, build_transcript,
)
from ..config import settings
from ..system_prompts import ARBITER_SYSTEM_PROMPT


class ArbiterAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.ARBITER, settings.ARBITER_MODEL, ARBITER_SYSTEM_PROMPT)

    async def process(self, context: dict) -> ProceedingEntry:
        round_num = context.get("current_round", 1)
        proceedings: List[ProceedingEntry] = context.get("proceedings", [])
        transcript = truncate_transcript(build_transcript(context))

        # Determine whether to issue verdict or preside
        aegis_count = sum(1 for p in proceedings if p.agent == AgentRole.AEGIS)
        axiom_count = sum(1 for p in proceedings if p.agent == AgentRole.AXIOM)
        metric_count = sum(1 for p in proceedings if p.agent == AgentRole.METRIC)
        max_rounds = settings.MAX_DEBATE_ROUNDS

        has_all_evidence = aegis_count >= 1 and axiom_count >= 1 and metric_count >= 1
        issue_verdict = (round_num >= max_rounds) or has_all_evidence

        if issue_verdict:
            return await self._issue_verdict(round_num, transcript, context)
        else:
            return await self._preside(round_num, transcript, max_rounds, context)

    async def _issue_verdict(self, round_num: int, transcript: str,
                             context: dict) -> ProceedingEntry:
        prompt = (
            "All evidence has been presented. Review the full transcript "
            "and issue your FINAL VERDICT in 3-4 sentences maximum.\n\n"
            f"Full transcript:\n{transcript}\n\n"
            "Provide scores for Security (0-10), Performance (0-10), "
            "Maintainability (0-10), and a definitive ruling "
            "(APPROVED / APPROVED WITH CONDITIONS / REJECTED). "
            "Speak with judicial authority. No bullet points, no emoji, no markdown."
        )
        content, usage = await self._call_llm(
            prompt, temperature=0.4, max_tokens=2000,
        )
        context.setdefault("token_usage", TokenUsageLog()).record(usage)
        return self._entry("Final Verdict", content, round_num, 0.9)

    async def _preside(self, round_num: int, transcript: str,
                       max_rounds: int, context: dict) -> ProceedingEntry:
        prompt = (
            f"Debate round {round_num} of {max_rounds} is in progress.\n\n"
            f"Transcript so far:\n{transcript}\n\n"
            "Provide a brief procedural ruling in 2 sentences: "
            "should the debate continue, or is more evidence needed? "
            "Speak with judicial authority. No bullet points, no emoji."
        )
        content, usage = await self._call_llm(
            prompt, temperature=0.5, max_tokens=500,
        )
        context.setdefault("token_usage", TokenUsageLog()).record(usage)
        return self._entry("Presiding", content, round_num, 0.8)
