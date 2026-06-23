"""
CodeTribunal - AXIOM Agent (The Defense Attorney)
Counters AEGIS's claims with real evidence from validation pattern detection.
Produces structured AgentFinding objects for conflict detection.
"""

import logging
from .base import (
    BaseAgent, AgentRole, ProceedingEntry, AgentFinding,
    TokenUsageLog, truncate_transcript, build_transcript, TrialPhase,
)
from .code_chunker import chunk_code, build_chunked_code
from .tools import ValidationDetector
from ..config import settings
from ..system_prompts import AXIOM_SYSTEM_PROMPT

logger = logging.getLogger("codetribunal.agents")


class AxiomAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.AXIOM, settings.AXIOM_MODEL, AXIOM_SYSTEM_PROMPT)

    async def process(self, context: dict) -> ProceedingEntry:
        raw_code = context.get("code_content", "")
        language = context.get("language", "unknown")
        round_num = context.get("current_round", 1)
        transcript = truncate_transcript(build_transcript(context))

        # Run validation detector for real defense evidence
        validation_patterns = ValidationDetector.detect(raw_code)
        if validation_patterns:
            logger.info(f"AXIOM: found {len(validation_patterns)} validation patterns")

        # Semantic chunking
        chunks = chunk_code(raw_code, language)
        chunked_code = build_chunked_code(chunks)

        # Build validation evidence for LLM prompt
        validation_evidence = ValidationDetector.format_patterns(validation_patterns)

        # Cross-examination context with prior testimony
        cross_exam_context = ""
        if round_num > 1 and context.get("conflict_clusters"):
            clusters = context["conflict_clusters"]
            relevant = [c for c in clusters if not c.resolved
                        and "AXIOM" in c.agents_involved]
            if relevant:
                # Extract AXIOM's own prior testimony to prevent repetition
                prior_statements = [
                    p for p in context.get("proceedings", [])
                    if p.agent == AgentRole.AXIOM
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
                        "Instead, respond ONLY to the new arguments below.\n"
                    )
                cross_exam_context += "Prosecution's NEW arguments:\n"
                for cluster in relevant:
                    other_claims = [
                        f.claim for f in cluster.findings
                        if f.agent != "AXIOM" and not f.withdrawn
                    ]
                    cross_exam_context += (
                        f"\nRegarding lines {cluster.line_start}-{cluster.line_end}:\n"
                    )
                    for claim in other_claims:
                        cross_exam_context += (
                            f"  Prosecution claims: {claim}\n"
                            f"  Respond with NEW evidence or concede the point.\n"
                        )

        # Build AEGIS's claims for AXIOM to counter
        aegis_claims = ""
        all_findings = context.get("all_findings", [])
        aegis_findings = [f for f in all_findings if f.agent == "AEGIS"]
        if aegis_findings:
            claim_lines = ["AEGIS has made these accusations:"]
            for af in aegis_findings:
                claim_lines.append(
                    f"  - Lines {af.line_start}-{af.line_end}: {af.claim} "
                    f"(confidence: {af.confidence}, source: {af.evidence_source})"
                )
            aegis_claims = "\n".join(claim_lines)

        prompt = (
            f"You are defending the following {language} code.\n\n"
            f"```{language}\n{chunked_code}\n```\n\n"
        )
        if aegis_claims:
            prompt += f"{aegis_claims}\n\n"
        if validation_patterns:
            prompt += f"Your evidence:\n{validation_evidence}\n\n"
        if transcript:
            prompt += f"Full tribunal transcript so far:\n{transcript}\n\n"
        if cross_exam_context:
            prompt += f"{cross_exam_context}\n\n"
        prompt += (
            "Respond to AEGIS's accusations in 2-3 sentences maximum. "
            "For each accusation, state: the line range, whether you object or concede, "
            "and your confidence (0.0-1.0). "
            "If valid, acknowledge and propose mitigation. "
            "If invalid, object with a clear 'Objection, Your Honor!' and reference "
            "specific validation patterns found in the code. "
            "No bullet points, no emoji."
        )

        content, usage = await self._call_llm(prompt, temperature=0.6)
        context.setdefault("token_usage", TokenUsageLog()).record(usage)

        # Build structured findings from validation patterns + LLM
        findings = []
        finding_counter = 0

        # Validation patterns are real defense evidence
        for vp in validation_patterns:
            finding_counter += 1
            findings.append(AgentFinding(
                finding_id=f"AXIOM-F{finding_counter:03d}",
                agent="AXIOM",
                category="validation",
                severity="low",  # Defense evidence = low severity (it's protected)
                line_start=vp.line_start,
                line_end=vp.line_end,
                claim=f"Defense evidence: {vp.description}",
                evidence_source=f"validator:{vp.pattern_type}",
                confidence=0.85,
                tool_data={
                    "pattern_type": vp.pattern_type,
                    "protects_against": vp.protects_against,
                },
            ))

        # Counter-findings for each AEGIS claim
        for af in aegis_findings:
            # Check if any validation pattern protects this line
            defense = ValidationDetector.find_defense_for_line(
                af.line_start, validation_patterns
            )
            finding_counter += 1
            if defense:
                findings.append(AgentFinding(
                    finding_id=f"AXIOM-F{finding_counter:03d}",
                    agent="AXIOM",
                    category="security",
                    severity="low",
                    line_start=af.line_start,
                    line_end=af.line_end,
                    claim=(
                        f"Objection: The code at lines {af.line_start}-{af.line_end} "
                        f"is protected by {defense.description} at line {defense.line_start}"
                    ),
                    evidence_source=f"validator:{defense.pattern_type}",
                    confidence=0.8,
                    tool_data={"defends_against": af.finding_id},
                ))
            else:
                # No tool-backed defense — concede with LLM reasoning
                has_objection = "objection" in content.lower()
                findings.append(AgentFinding(
                    finding_id=f"AXIOM-F{finding_counter:03d}",
                    agent="AXIOM",
                    category="security",
                    severity="medium" if has_objection else "low",
                    line_start=af.line_start,
                    line_end=af.line_end,
                    claim=content[:200],
                    evidence_source="llm_analysis",
                    confidence=0.7 if has_objection else 0.4,
                    tool_data={"responds_to": af.finding_id},
                ))

        # If no AEGIS findings to counter, still produce a defense statement
        if not findings:
            finding_counter += 1
            lines = raw_code.split("\n")
            findings.append(AgentFinding(
                finding_id=f"AXIOM-F{finding_counter:03d}",
                agent="AXIOM",
                category="security",
                severity="low",
                line_start=1,
                line_end=len(lines),
                claim=content[:200],
                evidence_source="llm_analysis",
                confidence=0.6,
            ))

        # Store findings in context
        context.setdefault("all_findings", []).extend(findings)

        # Determine if this is an objection
        is_objection = any("objection" in f.claim.lower() for f in findings)
        primary_line = findings[0].line_start if findings else 1
        exhibit_ref = f"Exhibit D-{finding_counter}" if findings else ""

        return self._entry(
            "Counter-Argument" if round_num == 1 else "Cross-Examination",
            content, round_num,
            max(f.confidence for f in findings) if findings else 0.6,
            phase=TrialPhase.INVESTIGATION if round_num == 1 else TrialPhase.CROSS_EXAMINATION,
            speaker=self.name,
            exhibit_ref=exhibit_ref,
            is_objection=is_objection,
            findings=findings,
            line_range=[findings[0].line_start, findings[0].line_end] if findings else None,
        )
