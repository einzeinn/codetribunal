"""
CodeTribunal - METRIC Agent (The Expert Witness)
Analyzes performance characteristics and code complexity using radon.
Produces structured AgentFinding objects with real numeric evidence.
"""

import logging
from .base import (
    BaseAgent, AgentRole, ProceedingEntry, AgentFinding,
    TokenUsageLog, truncate_transcript, build_transcript, TrialPhase,
)
from .code_chunker import chunk_code, build_structural_overview, build_chunked_code
from .tools import RadonRunner
from ..config import settings
from ..system_prompts import METRIC_SYSTEM_PROMPT

logger = logging.getLogger("codetribunal.agents")


class MetricAgent(BaseAgent):
    METRIC_MAX_TOKENS = 2500

    def __init__(self):
        super().__init__(AgentRole.METRIC, settings.METRIC_MODEL, METRIC_SYSTEM_PROMPT)

    async def process(self, context: dict) -> ProceedingEntry:
        raw_code = context.get("code_content", "")
        language = context.get("language", "unknown")
        round_num = context.get("current_round", 1)
        transcript = truncate_transcript(build_transcript(context))

        # Run radon for real complexity metrics (Python only)
        radon_findings = []
        if language.lower() in ("python", "py"):
            radon_findings = RadonRunner.run(raw_code)
            if radon_findings:
                logger.info(f"METRIC: radon found {len(radon_findings)} complexity issues")

        # Semantic chunking for LLM context
        chunks = chunk_code(raw_code, language)
        overview = build_structural_overview(chunks)
        chunked_code = build_chunked_code(chunks)

        # Build radon evidence block
        radon_evidence = ""
        if radon_findings:
            radon_lines = ["Radon complexity analysis found:"]
            for rf in radon_findings:
                radon_lines.append(
                    f"  - [{rf.severity.upper()}] {rf.rule_id} at lines {rf.line_start}-{rf.line_end}: "
                    f"{rf.message} ({rf.evidence})"
                )
            radon_evidence = "\n".join(radon_lines)

        # Cross-examination context with prior testimony
        cross_exam_context = ""
        if round_num > 1 and context.get("conflict_clusters"):
            clusters = context["conflict_clusters"]
            relevant = [c for c in clusters if not c.resolved
                        and "METRIC" in c.agents_involved]
            if relevant:
                prior_statements = [
                    p for p in context.get("proceedings", [])
                    if p.agent == AgentRole.METRIC
                ]
                prior_text = "\n".join(
                    f"  [Round {p.round_number}]: {p.message[:150]}..."
                    for p in prior_statements
                ) if prior_statements else ""

                cross_exam_context = "\nCROSS-EXAMINATION INSTRUCTIONS:\n"
                if prior_text:
                    cross_exam_context += (
                        f"You previously testified:\n{prior_text}\n\n"
                        "DO NOT repeat these arguments verbatim. "
                        "Respond ONLY to new questions below.\n"
                    )
                cross_exam_context += "Other agents' NEW claims:\n"
                for cluster in relevant:
                    other_claims = [
                        f.claim for f in cluster.findings
                        if f.agent != "METRIC" and not f.withdrawn
                    ]
                    cross_exam_context += (
                        f"\nRegarding lines {cluster.line_start}-{cluster.line_end}:\n"
                    )
                    for claim in other_claims:
                        cross_exam_context += (
                            f"  Another agent claims: {claim}\n"
                            f"  Does your radon data support or contradict? Cite numbers.\n"
                        )

        prompt = (
            f"Analyze the performance and complexity of this {language} code.\n\n"
            f"{overview}\n\n"
        )
        if radon_evidence:
            prompt += f"{radon_evidence}\n\n"
        prompt += f"```{language}\n{chunked_code}\n```\n\n"

        if transcript:
            prompt += f"Previous proceedings:\n{transcript}\n\n"
        if cross_exam_context:
            prompt += f"{cross_exam_context}\n\n"
        prompt += (
            "Provide ONE key finding only, in 2 sentences maximum. "
            "Include a complexity rating (1-10) and one specific issue. "
            "If radon data is available, cite the actual cyclomatic complexity numbers. "
            "Speak as an expert witness, not a technical report. No bullet points, no emoji."
        )

        content, usage = await self._call_llm(
            prompt, temperature=0.5, max_tokens=self.METRIC_MAX_TOKENS,
        )
        context.setdefault("token_usage", TokenUsageLog()).record(usage)

        # Build structured findings from radon + LLM
        findings = []
        finding_counter = 0

        # Radon findings are authoritative numeric evidence
        for rf in radon_findings:
            finding_counter += 1
            findings.append(AgentFinding(
                finding_id=f"METRIC-F{finding_counter:03d}",
                agent="METRIC",
                category=rf.category,
                severity=rf.severity,
                line_start=rf.line_start,
                line_end=rf.line_end,
                claim=rf.message,
                evidence_source=f"radon:{rf.rule_id}",
                confidence=rf.confidence,
                tool_data={"tool": "radon", "rule": rf.rule_id},
            ))

        # If radon found nothing, LLM still provides analysis
        if not findings:
            finding_counter += 1
            lines = raw_code.split("\n")
            findings.append(AgentFinding(
                finding_id=f"METRIC-F{finding_counter:03d}",
                agent="METRIC",
                category="complexity",
                severity="medium",
                line_start=1,
                line_end=len(lines),
                claim=content[:200],
                evidence_source="llm_analysis",
                confidence=0.65,
            ))

        # Store findings in context
        context.setdefault("all_findings", []).extend(findings)

        primary_line = findings[0].line_start if findings else 1
        exhibit_ref = f"Exhibit M-{finding_counter}" if findings else ""

        return self._entry(
            "Evidence", content, round_num,
            findings[0].confidence if findings else 0.75,
            phase=TrialPhase.INVESTIGATION if round_num == 1 else TrialPhase.CROSS_EXAMINATION,
            speaker=self.name,
            exhibit_ref=exhibit_ref,
            findings=findings,
            line_range=[findings[0].line_start, findings[0].line_end] if findings else None,
        )
