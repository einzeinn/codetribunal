"""
CodeTribunal - AEGIS Agent (The Prosecutor)
Hunts for security vulnerabilities using bandit + LLM reasoning.
Produces structured AgentFinding objects with real tool evidence.
"""

import logging
from .base import (
    BaseAgent, AgentRole, ProceedingEntry, AgentFinding,
    TokenUsageLog, truncate_transcript, build_transcript, build_cluster_history,
    TrialPhase,
)
from .code_chunker import chunk_code, build_structural_overview, build_chunked_code
from .tools import BanditRunner
from ..config import settings
from ..system_prompts import AEGIS_SYSTEM_PROMPT

logger = logging.getLogger("codetribunal.agents")


class AegisAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.AEGIS, settings.AEGIS_MODEL, AEGIS_SYSTEM_PROMPT)

    async def process(self, context: dict) -> ProceedingEntry:
        raw_code = context.get("code_content", "")
        language = context.get("language", "unknown")
        round_num = context.get("current_round", 1)
        transcript = truncate_transcript(build_transcript(context))

        # Phase 1: Run bandit for real security findings (Python only)
        bandit_findings = []
        if language.lower() in ("python", "py"):
            bandit_findings = BanditRunner.run(raw_code)
            if bandit_findings:
                logger.info(f"AEGIS: bandit found {len(bandit_findings)} issues")

        # Semantic chunking for LLM context
        chunks = chunk_code(raw_code, language)
        overview = build_structural_overview(chunks)
        chunked_code = build_chunked_code(chunks)

        # Build bandit evidence block for LLM prompt
        bandit_evidence = ""
        if bandit_findings:
            bandit_lines = ["Bandit security scanner found these issues:"]
            for bf in bandit_findings:
                bandit_lines.append(
                    f"  - [{bf.severity.upper()}] {bf.rule_id} at line {bf.line_start}: "
                    f"{bf.message} ({bf.evidence})"
                )
            bandit_evidence = "\n".join(bandit_lines)

        # Cross-examination context with prior testimony
        cross_exam_context = ""
        if round_num > 1 and context.get("conflict_clusters"):
            clusters = context["conflict_clusters"]

            # Show UNRESOLVED clusters (active debates)
            unresolved = [c for c in clusters if not c.resolved
                         and "AEGIS" in c.agents_involved]

            # ALSO show RESOLVED clusters where AEGIS conceded or lost
            # This prevents AEGIS from re-arguing defeated points
            resolved_aegis = [c for c in clusters if c.resolved
                             and "AEGIS" in [f.agent for f in c.findings]]

            # Build list of AEGIS findings that were withdrawn/conceded
            conceded_findings = []
            for c in resolved_aegis:
                for f in c.findings:
                    if f.agent == "AEGIS" and f.withdrawn:
                        conceded_findings.append(f)

            if unresolved or conceded_findings:
                cross_exam_context = "\nCROSS-EXAMINATION INSTRUCTIONS:\n"

                # ── DEFEATED FINDINGS (critical for memory) ──
                if conceded_findings:
                    cross_exam_context += (
                        "═══ DEFEATED FINDINGS (DO NOT RE-ARGUE) ═══\n"
                        "The following findings were REJECTED during cross-examination.\n"
                        "Do NOT repeat these arguments. Do NOT re-raise them.\n"
                        "The court has already ruled against them:\n"
                    )
                    for f in conceded_findings:
                        cross_exam_context += (
                            f"  ✗ {f.finding_id} (lines {f.line_start}-{f.line_end}): "
                            f"{f.claim[:100]}\n"
                            f"    Reason for rejection: {f.rebuttal[:120] if f.rebuttal else 'defense proved non-usage via AST analysis'}\n"
                            f"    Your confidence was: {f.confidence}\n"
                        )
                    cross_exam_context += (
                        "═══════════════════════════════════════════\n"
                        "IMPORTANT: These findings are DEAD. Do not mention them again.\n"
                        "Focus ONLY on findings that have NOT been defeated.\n\n"
                    )

                # ── Active debates ──
                if unresolved:
                    cluster_history = build_cluster_history(clusters, agent_name="AEGIS")

                    # Extract AEGIS's own prior testimony to prevent repetition
                    prior_statements = [
                        p for p in context.get("proceedings", [])
                        if p.agent == AgentRole.AEGIS
                    ]
                    prior_text = "\n".join(
                        f"  [Round {p.round_number}]: {p.message[:150]}..."
                        for p in prior_statements
                    ) if prior_statements else ""

                    if cluster_history:
                        cross_exam_context += f"{cluster_history}\n\n"
                    if prior_text:
                        cross_exam_context += (
                            f"You previously testified:\n{prior_text}\n\n"
                            "DO NOT repeat these arguments verbatim. "
                            "Instead, respond ONLY to the new counter-arguments below.\n"
                        )
                    cross_exam_context += (
                        "CONCESSION RULES (FOLLOW STRICTLY):\n"
                        "- If the defense provides AST-level or tool-level proof that a "
                        "function/import is NEVER USED (e.g., 'AST analysis shows subprocess "
                        "is never called anywhere in the code'), you MUST lower your confidence "
                        "to 0.2 or below — this is a confirmed false positive.\n"
                        "- 'Its mere presence suggests potential future misuse' is NOT a valid "
                        "counter-argument against AST proof of non-usage. Do NOT use this reasoning.\n"
                        "- If your original finding was based on code presence but the defense "
                        "proved the code is dead/unused, CONCEDE honestly.\n"
                        "- Only maintain high confidence if you have NEW evidence that "
                        "directly counters the defense's specific proof.\n\n"
                    )
                    cross_exam_context += "Opposing counsel's NEW counter-arguments:\n"
                    for cluster in unresolved:
                        other_claims = [
                            f.claim for f in cluster.findings
                            if f.agent != "AEGIS" and not f.withdrawn
                        ]
                        cross_exam_context += (
                            f"\nRegarding lines {cluster.line_start}-{cluster.line_end}:\n"
                        )
                        for claim in other_claims:
                            cross_exam_context += (
                                f"  Defense claims: {claim}\n"
                                f"  Respond with NEW counter-evidence or revise your confidence.\n"
                            )

        prompt = (
            f"Review the following {language} code for security vulnerabilities.\n\n"
            f"{overview}\n\n"
        )
        if bandit_evidence:
            prompt += f"{bandit_evidence}\n\n"
        prompt += f"Full chunked source:\n```{language}\n{chunked_code}\n```\n\n"

        if transcript:
            prompt += f"Previous proceedings:\n{transcript}\n\n"
        if cross_exam_context:
            prompt += f"{cross_exam_context}\n\n"
        prompt += (
            "Present your findings to the court. Keep it under 3 sentences per finding. "
            "For EACH finding, state: the line range, the vulnerability type, "
            "and your confidence (0.0-1.0). "
            "Cite specific chunk names and line numbers with dramatic flair. "
            "No bullet points, no emoji, no markdown."
        )

        content, usage = await self._call_llm(prompt)
        context.setdefault("token_usage", TokenUsageLog()).record(usage)

        # Build structured findings from bandit + LLM synthesis
        findings = []
        finding_counter = 0
        total_lines = context.get("total_lines", 0) or len(raw_code.split("\n"))

        # Bandit findings are authoritative tool evidence
        for bf in bandit_findings:
            finding_counter += 1
            # Clamp line ranges to actual file length
            ls = max(1, min(bf.line_start, total_lines))
            le = max(ls, min(bf.line_end, total_lines))
            findings.append(AgentFinding(
                finding_id=f"AEGIS-F{finding_counter:03d}",
                agent="AEGIS",
                category="security",
                severity=bf.severity,
                line_start=ls,
                line_end=le,
                claim=bf.message,
                evidence_source=f"bandit:{bf.rule_id}",
                confidence=bf.confidence,
                tool_data={"rule_id": bf.rule_id, "tool": "bandit"},
            ))

        # If bandit found nothing, LLM still gets to flag issues
        # but with lower confidence (no tool backing)
        if not findings:
            finding_counter += 1
            # Extract line numbers from LLM response for basic structuring
            lines = raw_code.split("\n")
            findings.append(AgentFinding(
                finding_id=f"AEGIS-F{finding_counter:03d}",
                agent="AEGIS",
                category="security",
                severity="medium",
                line_start=1,
                line_end=len(lines),
                claim=content[:200],  # Truncate for structured storage
                evidence_source="llm_analysis",
                confidence=0.65,
            ))

        # Store findings in context for orchestrator conflict detection
        context.setdefault("all_findings", []).extend(findings)

        # Determine exhibit reference
        primary_line = findings[0].line_start if findings else 1
        exhibit_ref = f"Exhibit A-{finding_counter}" if findings else ""

        return self._entry(
            "Opening" if round_num == 1 else "Cross-Examination",
            content, round_num, findings[0].confidence if findings else 0.7,
            phase=TrialPhase.INVESTIGATION if round_num == 1 else TrialPhase.CROSS_EXAMINATION,
            speaker=self.name,
            exhibit_ref=exhibit_ref,
            findings=findings,
            line_range=[findings[0].line_start, findings[0].line_end] if findings else None,
        )
