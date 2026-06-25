"""
CodeTribunal - ARBITER Agent (The Judge)
Issues per-item verdicts with reasoning trails based on structured findings
and conflict cluster outcomes. Orchestrates the final ruling.

Verdict flow (post-fix):
  1. LLM writes per-finding verdicts (CONFIRMED/DISMISSED/DISPUTED)
  2. Parse statuses from LLM response -> mark findings
  3. Compute scores from marked findings (dismissed = no penalty)
  4. Compute verdict from scores
  5. Append score block to verdict text
"""

import re
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

        # Issue per-item verdict (scores computed AFTER LLM rules on each finding)
        return await self._issue_verdict(
            round_num, transcript,
            all_findings, conflict_clusters, context
        )

    async def _issue_verdict(
        self, round_num: int, transcript: str,
        all_findings: List[AgentFinding],
        conflict_clusters: List[ConflictCluster],
        context: dict,
    ) -> ProceedingEntry:
        # ── Pass 1: Deduplicate findings by finding_id ──
        # Safety net: cross-exam rounds may produce duplicate entries in all_findings.
        seen_ids = set()
        deduped_findings = []
        for f in all_findings:
            if f.finding_id not in seen_ids:
                seen_ids.add(f.finding_id)
                deduped_findings.append(f)
        if len(deduped_findings) < len(all_findings):
            logger.info(
                f"Pass-1 dedup (finding_id): {len(all_findings)} -> {len(deduped_findings)}"
            )

        # ── Pass 2: Semantic dedup — collapse findings that argue the same point ──
        # AXIOM generates NEW finding_ids every cross-exam round for the SAME
        # underlying argument (e.g. AXIOM-F002 R1, AXIOM-F006 R2, AXIOM-F009 R3
        # all defend "API_TOKEN is not a password"). Keep the LAST occurrence
        # (latest round) because it carries the most up-to-date confidence/rebuttal
        # from cross-examination.
        semantic_seen: dict = {}  # key -> index in deduped list (last wins)
        for i, f in enumerate(deduped_findings):
            # NOTE: line_end is EXCLUDED from the key because AXIOM may shift
            # its line_end across rounds (e.g. 27-30 in R1, 30-35 in R3) while
            # arguing the same underlying point. agent+line_start+claim prefix
            # is sufficient to identify a unique argument.
            key = (f.agent, f.line_start, f.claim[:50].lower())
            semantic_seen[key] = i  # overwrite → keep last
        kept_indices = sorted(semantic_seen.values())
        semantic_deduped = [deduped_findings[i] for i in kept_indices]
        if len(semantic_deduped) < len(deduped_findings):
            removed = len(deduped_findings) - len(semantic_deduped)
            logger.info(
                f"Pass-2 semantic dedup: {len(deduped_findings)} -> {len(semantic_deduped)} "
                f"(collapsed {removed} repeated arguments)"
            )
        all_findings = semantic_deduped

        # Build per-finding evidence block for the LLM
        per_finding_evidence = self._build_per_finding_evidence(
            all_findings, conflict_clusters
        )

        # ── Step 1: Ask LLM to write per-finding verdicts FIRST ──
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
            "CRITICAL: Rule ONLY on the findings listed in the PER-FINDING EVIDENCE "
            "block above. Do NOT rule on any other finding IDs you may see mentioned "
            "in the transcript — those are earlier rounds of the same arguments and "
            "have been consolidated into the single representative ID shown above.\n\n"
            "INSTRUCTIONS FOR EACH FINDING:\n"
            "- State the finding ID and line range\n"
            "- Status: CONFIRMED, DISMISSED, or DISPUTED\n"
            "- Reference the SPECIFIC tool evidence or cross-exam argument that determined your ruling\n"
            "- If the finding was uncontested, cite why it stands alone\n"
            "- If it was cross-examined, cite what the opposing agent said and why one side won\n"
            "- Do NOT use the same phrasing for different findings — each ruling must reflect its unique evidence\n\n"
            "WHEN TO USE DISPUTED (IMPORTANT):\n"
            "- Use DISPUTED when the finding is TECHNICALLY VALID but the defense raised legitimate mitigating factors\n"
            "- Example: 'pickle.load() on local trusted files' — technically a risk, but defense showed files come from controlled source\n"
            "- Example: 'subprocess import present' but AST shows it's never called — if prosecution has some counter-evidence, rule DISPUTED\n"
            "- Example: 'SQL query pattern' but defense showed parameterized queries elsewhere — rule DISPUTED\n"
            "- DISPUTED means: the code pattern IS risky in general, but in THIS specific context the risk is reduced\n"
            "- Do NOT binary-force everything to CONFIRMED or DISMISSED — use DISPUTED for legitimate middle ground\n\n"
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
            "Keep each item ruling to 2-3 sentences.\n\n"
            "IMPORTANT: Do NOT write a final verdict word (no APPROVED, no APPROVED WITH "
            "CONDITIONS, no REJECTED). Do NOT write any numeric scores. Do NOT write a "
            "summary or concluding sentence. Stop immediately after your last per-finding "
            "ruling. The tribunal's official final verdict word and scores are computed "
            "deterministically by the system and will be appended after your response — "
            "writing your own would create a contradiction."
        )

        content, usage = await self._call_llm(
            prompt, temperature=0.4, max_tokens=2500,
        )
        context.setdefault("token_usage", TokenUsageLog()).record(usage)

        # ── Step 2: Parse per-finding statuses from LLM response ──
        verdict_statuses = self._parse_verdict_statuses(content, all_findings)
        logger.info(f"Parsed verdict statuses: {verdict_statuses}")

        # ── Step 3: Mark findings with verdict status ──
        for finding_id, status in verdict_statuses.items():
            for f in all_findings:
                if f.finding_id == finding_id:
                    f.verdict_status = status  # type: ignore[attr-defined]
                    if status == "DISMISSED":
                        f.withdrawn = True  # Dismissed = no scoring penalty
                    logger.info(
                        f"ARBITER verdict: {finding_id} -> {status}"
                    )
                    break

        # ── Step 4: Compute scores AFTER verdict (dismissed = no penalty) ──
        rubric = self._compute_rubric_scores(all_findings, conflict_clusters)

        # ── Step 5: Compute verdict from corrected scores ──
        verdict = self._compute_verdict(rubric)

        # ── Defensive backstop: strip any trailing verdict word the LLM wrote ──
        # Even though the prompt forbids it, LLMs sometimes disobey.
        # Strip a trailing line that is JUST "APPROVED", "APPROVED WITH CONDITIONS",
        # or "REJECTED" (case-insensitive) before appending the real score_block.
        content = content.rstrip()
        _TRAILING_VERDICT_RE = re.compile(
            r"\n\s*(APPROVED\s+WITH\s+CONDITIONS|APPROVED|REJECTED)\s*\.?\s*$",
            re.IGNORECASE,
        )
        content = _TRAILING_VERDICT_RE.sub("", content).rstrip()

        # ── Step 6: Append score block to verdict text ──
        score_block = (
            f"\n\nTRIBUNAL ASSESSMENT: "
            f"Security {rubric['security']}/10 ({rubric['security_detail']}). "
            f"Performance {rubric['performance']}/10 ({rubric['performance_detail']}). "
            f"Maintainability {rubric['maintainability']}/10 ({rubric['maintainability_detail']}). "
            f"Final ruling: {verdict}."
        )
        content = content + score_block

        # Build verdict proceeding with structured metadata
        primary_line = all_findings[0].line_start if all_findings else 1
        last_line = max(
            (f.line_end for f in all_findings), default=1
        )

        return self._entry(
            "Final Verdict", content, round_num, 0.9,
            phase=TrialPhase.VERDICT,
            speaker=self.name,
            exhibit_ref="Verdict Scroll",
            findings=all_findings,
            line_range=[primary_line, last_line],
            rubric_scores=rubric,
        )

    def _parse_verdict_statuses(
        self, verdict_text: str, all_findings: List[AgentFinding]
    ) -> dict:
        """
        Parse CONFIRMED/DISMISSED/DISPUTED statuses from LLM verdict text.
        Returns dict mapping finding_id -> status.
        Uses multiple regex patterns to handle varied LLM output formats.
        """
        statuses = {}
        finding_ids = {f.finding_id for f in all_findings}

        # Pattern 1: Direct format — "AEGIS-F001: CONFIRMED" or "AEGIS-F001 (lines 15-18): DISMISSED"
        # Pattern 2: With dash — "AEGIS-F001 - CONFIRMED"
        # Pattern 3: With em dash — "AEGIS-F001 — CONFIRMED"
        # Pattern 4: Sentence format — "AEGIS-F001 is CONFIRMED" or "AEGIS-F001 is ruled DISMISSED"
        # Pattern 5: Prefix format — "For AEGIS-F001: DISPUTED" or "Regarding AEGIS-F001: CONFIRMED"
        patterns = [
            # Direct: "AEGIS-F001: CONFIRMED" or "AEGIS-F001 (lines 15-18): DISMISSED"
            r"(AEGIS-F\d+|AXIOM-F\d+|METRIC-F\d+|LEDGER-F\d+)(?:\s*\([^)]*\))?\s*[-:—–]\s*(CONFIRMED|DISMISSED|DISPUTED)",
            # Sentence: "AEGIS-F001 is CONFIRMED" or "AEGIS-F001 is ruled DISMISSED"
            r"(AEGIS-F\d+|AXIOM-F\d+|METRIC-F\d+|LEDGER-F\d+)\s+(?:is\s+(?:ruled\s+)?|was\s+(?:ruled\s+)?)(CONFIRMED|DISMISSED|DISPUTED)",
            # Prefix: "For AEGIS-F001: DISPUTED" or "Regarding AEGIS-F001, CONFIRMED"
            r"(?:for|regarding|as\s+for)\s+(AEGIS-F\d+|AXIOM-F\d+|METRIC-F\d+|LEDGER-F\d+)[,:\s]+(?:ruled\s+)?(CONFIRMED|DISMISSED|DISPUTED)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, verdict_text, re.IGNORECASE)
            for match in matches:
                finding_id = match.group(1).upper()
                status = match.group(2).upper()
                if finding_id in finding_ids and finding_id not in statuses:
                    statuses[finding_id] = status

        # If no structured statuses found, fall back to heuristic:
        # withdrawn findings -> DISMISSED, others -> CONFIRMED
        if not statuses:
            for f in all_findings:
                if f.withdrawn:
                    statuses[f.finding_id] = "DISMISSED"
                else:
                    statuses[f.finding_id] = "CONFIRMED"
            logger.warning(
                "Could not parse verdict statuses from LLM response, "
                "using heuristic fallback"
            )
        else:
            # Fill in any missing findings not mentioned by LLM
            for f in all_findings:
                if f.finding_id not in statuses:
                    if f.withdrawn:
                        statuses[f.finding_id] = "DISMISSED"
                    else:
                        statuses[f.finding_id] = "CONFIRMED"
                    logger.info(
                        f"Finding {f.finding_id} not mentioned in verdict, "
                        f"defaulting to {statuses[f.finding_id]}"
                    )

        return statuses

    def _build_per_finding_evidence(
        self,
        findings: List[AgentFinding],
        clusters: List[ConflictCluster],
    ) -> str:
        """
        Build a per-finding evidence block with cross-exam outcomes.
        Gives the LLM specific context for each finding so it can produce
        differentiated reasoning instead of template text.

        NOTE: AXIOM/METRIC findings are deduplicated semantically here for
        verdict-text readability only. They are never included in
        _compute_rubric_scores (only AEGIS/METRIC security findings are),
        so this dedup does NOT change any numeric score. If it ever does
        affect a score, something else is reading AXIOM findings for
        scoring and that's a separate bug.
        """
        # ── Semantic dedup: collapse findings that argue the same point ──
        # AXIOM generates new finding_ids each cross-exam round for the same
        # underlying argument (e.g., AXIOM-F002 in R1, AXIOM-F006 in R2,
        # AXIOM-F009 in R3, all defending "API_TOKEN is not a password").
        # Key by (agent, line_start, line_end, first 50 chars of claim).
        seen_semantic = set()
        deduped = []
        for f in findings:
            key = (f.agent, f.line_start, f.claim[:50].lower())
            if key not in seen_semantic:
                seen_semantic.add(key)
                deduped.append(f)
        if len(deduped) < len(findings):
            logger.info(
                f"Semantic dedup in evidence block: {len(findings)} -> {len(deduped)} "
                f"(collapsed {len(findings) - len(deduped)} repeated arguments)"
            )
        findings = deduped

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

        Verdict status flow:
        - CONFIRMED: full penalty
        - DISMISSED: no penalty (excluded from scoring)
        - DISPUTED: 50% penalty (evidence inconclusive)

        Returns dict with security, performance, maintainability (0-10 each)
        plus human-readable detail strings.
        """
        # Filter findings by verdict status
        # DISMISSED findings have been marked withdrawn=True in _issue_verdict
        confirmed = [f for f in findings if not f.withdrawn and getattr(f, 'verdict_status', 'CONFIRMED') == 'CONFIRMED']
        disputed = [f for f in findings if getattr(f, 'verdict_status', None) == 'DISPUTED']
        dismissed = [f for f in findings if getattr(f, 'verdict_status', None) == 'DISMISSED']

        # Count total non-info findings for dismissal ratio
        total_actionable = [f for f in findings if f.severity != "info"]
        dismissal_ratio = len(dismissed) / max(len(total_actionable), 1)

        logger.info(
            f"Scoring breakdown: {len(confirmed)} confirmed, {len(disputed)} disputed, "
            f"{len(dismissed)} dismissed (ratio: {dismissal_ratio:.0%})"
        )

        # ── Security Score ─────────────────────────────────────────
        # Penalise confirmed security findings by severity weight.
        # NOTE: Only AEGIS and METRIC findings count toward security penalty.
        # AXIOM findings are defense arguments and are NEVER included in scoring.
        # This is an intentional invariant — AXIOM dedup in _build_per_finding_evidence
        # is purely for verdict-text readability and cannot affect this score.
        sec_confirmed = [
            f for f in confirmed
            if f.category == "security" and f.agent in ("AEGIS", "METRIC")
        ]
        sec_disputed = [
            f for f in disputed
            if f.category == "security" and f.agent in ("AEGIS", "METRIC")
        ]
        severity_weights = {"critical": 3, "high": 2, "medium": 1, "low": 0.5}
        sec_penalty = sum(severity_weights.get(f.severity, 0.5) for f in sec_confirmed)
        sec_penalty += 0.5 * sum(severity_weights.get(f.severity, 0.5) for f in sec_disputed)  # 50% for disputed
        security = max(0, min(10, round(10 - sec_penalty)))

        # Proportional floor: if findings were dismissed, security should reflect
        # that the prosecution partially lost. E.g., dismissing 1/6 findings = floor of 1-2.
        if dismissal_ratio > 0 and sec_penalty > 0:
            dismissal_floor = round(10 * dismissal_ratio * 0.5)  # 50% credit for dismissals
            security = max(security, dismissal_floor)
            if dismissal_floor > 0:
                logger.info(
                    f"Security dismissal floor applied: {dismissal_floor} "
                    f"(dismissed {len(dismissed)}/{len(total_actionable)} findings)"
                )

        security_detail = (
            f"{len(sec_confirmed)} confirmed + {len(sec_disputed)} disputed security findings, "
            f"penalty {sec_penalty:.1f}"
        )

        # ── Performance Score ──────────────────────────────────────
        # Penalise high/medium complexity findings from METRIC (radon)
        perf_confirmed = [
            f for f in confirmed
            if f.category == "complexity"
            or (f.agent == "METRIC" and f.category != "security")
        ]
        perf_disputed = [
            f for f in disputed
            if f.category == "complexity"
            or (f.agent == "METRIC" and f.category != "security")
        ]
        high_cc = sum(1 for f in perf_confirmed if f.severity == "critical")
        med_cc = sum(1 for f in perf_confirmed if f.severity in ("high", "medium"))
        high_cc += 0.5 * sum(1 for f in perf_disputed if f.severity == "critical")
        med_cc += 0.5 * sum(1 for f in perf_disputed if f.severity in ("high", "medium"))
        perf_penalty = high_cc * 1.5 + med_cc * 0.5
        performance = max(0, min(10, round(10 - perf_penalty)))
        performance_detail = (
            f"{high_cc:.1f} high-complexity functions, "
            f"{med_cc:.1f} medium-complexity, penalty {perf_penalty:.1f}"
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
