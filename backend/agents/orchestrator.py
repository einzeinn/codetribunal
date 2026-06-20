"""
CodeTribunal - Tribunal Court (Orchestrator)
Conditional multi-agent protocol with parallel investigation,
deterministic conflict detection, and targeted cross-examination.

Protocol phases:
  1. LEDGER files the case (AST structural parsing)
  2. PARALLEL INVESTIGATION — AEGIS, AXIOM, METRIC run concurrently
  3. CONFLICT DETECTION — deterministic line-range overlap analysis
  4. CROSS-EXAMINATION — only conflicting agents debate, per-cluster
  5. VERDICT — ARBITER rules per-item with reasoning trail
"""

import asyncio
import logging
from typing import List, Optional

from .base import (
    AgentRole, ProceedingEntry, TokenUsageLog,
    AgentFinding, ConflictCluster, TrialPhase,
)
from .ledger import LedgerAgent
from .aegis import AegisAgent
from .axiom import AxiomAgent
from .metric import MetricAgent
from .arbiter import ArbiterAgent
from ..config import settings

logger = logging.getLogger("codetribunal.agents")

# Line range overlap tolerance for conflict detection
_OVERLAP_TOLERANCE = 3  # lines


class TribunalCourt:
    """
    Orchestrates the conditional multi-agent adversarial code review.

    Unlike the previous linear pipeline, this orchestrator:
    - Runs AEGIS, AXIOM, METRIC in parallel (asyncio.gather)
    - Detects conflicts deterministically (no LLM call)
    - Only sends conflicting findings to cross-examination
    - ARBITER rules per-item, not globally
    """

    def __init__(self):
        self.agents = {
            AgentRole.LEDGER: LedgerAgent(),
            AgentRole.AEGIS: AegisAgent(),
            AgentRole.AXIOM: AxiomAgent(),
            AgentRole.METRIC: MetricAgent(),
            AgentRole.ARBITER: ArbiterAgent(),
        }
        self.proceedings: List[ProceedingEntry] = []
        self.token_usage = TokenUsageLog()
        self.all_findings: List[AgentFinding] = []
        self.conflict_clusters: List[ConflictCluster] = []
        self._cancelled = False
        self._current_task: asyncio.Task | None = None

    def cancel(self):
        """Signal the trial to stop AND abort any in-flight API request."""
        self._cancelled = True
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            logger.info("TribunalCourt: cancelled in-flight API request.")
        logger.info("TribunalCourt: trial cancelled.")

    # ═════════════════════════════════════════════════════════════════
    # Streaming entry point (primary — used by WebSocket)
    # ═════════════════════════════════════════════════════════════════

    async def conduct_trial_streaming(
        self, code_content: str, language: str = "unknown", focus_area: str = ""
    ):
        """
        Async generator — yields each ProceedingEntry as it completes.
        Implements the full conditional protocol.
        """
        context = self._build_context(code_content, language, focus_area)

        try:
            # ── Phase 0: LEDGER files the case ──────────────────────
            entry = await self._run_agent_safe(AgentRole.LEDGER, context)
            if entry is None:
                return
            yield entry

            # ── Phase 1: Parallel Investigation ─────────────────────
            for entry in self._emit_phase_banner(TrialPhase.INVESTIGATION):
                yield entry

            investigation_results = await self._run_parallel_investigation(context)
            for entry in investigation_results:
                if entry is None:
                    return
                yield entry

            # ── Phase 2: Deterministic Conflict Detection ───────────
            for entry in self._emit_phase_banner(TrialPhase.CONFLICT_DETECTION):
                yield entry

            self.conflict_clusters = self._detect_conflicts(self.all_findings)
            context["conflict_clusters"] = self.conflict_clusters

            # Emit conflict detection summary
            conflict_entry = self._build_conflict_summary_entry()
            self.proceedings.append(conflict_entry)
            yield conflict_entry

            # ── Phase 3: Targeted Cross-Examination (conditional) ───
            active_clusters = [c for c in self.conflict_clusters if c.has_conflict]
            if active_clusters:
                for entry in self._emit_phase_banner(TrialPhase.CROSS_EXAMINATION):
                    yield entry

                async for entry in self._run_cross_examination(context, active_clusters):
                    if entry is None:
                        return
                    yield entry

            # ── Phase 4: Verdict ────────────────────────────────────
            for entry in self._emit_phase_banner(TrialPhase.VERDICT):
                yield entry

            # Prepare context for ARBITER with all findings and clusters
            context["all_findings"] = self.all_findings
            context["conflict_clusters"] = self.conflict_clusters
            context["trial_phase"] = TrialPhase.VERDICT

            entry = await self._run_agent_safe(AgentRole.ARBITER, context)
            if entry is None:
                return
            yield entry

        except asyncio.CancelledError:
            logger.info("Trial streaming cancelled by event loop.")
            self._cancelled = True
            raise

    # ═════════════════════════════════════════════════════════════════
    # Blocking entry point (REST API)
    # ═════════════════════════════════════════════════════════════════

    async def conduct_trial(
        self, code_content: str, language: str = "unknown", focus_area: str = ""
    ) -> List[ProceedingEntry]:
        """Run a complete trial and return all proceedings (blocking)."""
        async for _entry in self.conduct_trial_streaming(
            code_content, language, focus_area
        ):
            pass  # collect into self.proceedings
        return self.proceedings

    # ═════════════════════════════════════════════════════════════════
    # Phase 1: Parallel Investigation
    # ═════════════════════════════════════════════════════════════════

    async def _run_parallel_investigation(self, context: dict) -> List[Optional[ProceedingEntry]]:
        """
        Run AEGIS, AXIOM, METRIC concurrently via asyncio.gather.
        Each agent independently scans the code with their own tools.
        Returns list of ProceedingEntry (in order: AEGIS, AXIOM, METRIC).
        """
        if self._cancelled:
            return [None, None, None]

        # Create separate tasks for parallel execution
        aegis_task = asyncio.create_task(
            self._run_agent(AgentRole.AEGIS, context)
        )
        axiom_task = asyncio.create_task(
            self._run_agent(AgentRole.AXIOM, context)
        )
        metric_task = asyncio.create_task(
            self._run_agent(AgentRole.METRIC, context)
        )

        self._current_task = None  # parallel — can't cancel one specifically

        try:
            results = await asyncio.gather(
                aegis_task, axiom_task, metric_task,
                return_exceptions=True,
            )
        except asyncio.CancelledError:
            self._cancelled = True
            for t in [aegis_task, axiom_task, metric_task]:
                if not t.done():
                    t.cancel()
            return [None, None, None]

        entries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                role = [AgentRole.AEGIS, AgentRole.AXIOM, AgentRole.METRIC][i]
                logger.error(f"Agent {role.value} failed: {result}")
                entries.append(None)
            elif isinstance(result, ProceedingEntry):
                self.proceedings.append(result)
                entries.append(result)
                # Collect findings
                if result.findings:
                    self.all_findings.extend(result.findings)
            else:
                entries.append(None)

        context["proceedings"] = self.proceedings
        context["all_findings"] = self.all_findings
        return entries

    # ═════════════════════════════════════════════════════════════════
    # Phase 2: Deterministic Conflict Detection (no LLM)
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _detect_conflicts(findings: List[AgentFinding]) -> List[ConflictCluster]:
        """
        Compare findings from different agents for line-range overlap.
        Only findings that overlap AND disagree become conflict clusters.
        Non-conflicting findings skip directly to the verdict.

        This is deterministic code — no LLM call needed.
        """
        if not findings:
            return []

        clusters: List[ConflictCluster] = []
        used = set()  # finding_ids already clustered
        cluster_counter = 0

        # Sort findings by line_start for efficient overlap scanning
        sorted_findings = sorted(findings, key=lambda f: f.line_start)

        for i, f1 in enumerate(sorted_findings):
            if f1.finding_id in used:
                continue

            # Find all overlapping findings from OTHER agents
            overlapping = [f1]
            for j, f2 in enumerate(sorted_findings):
                if i == j or f2.finding_id in used:
                    continue
                if f2.agent == f1.agent:
                    continue  # Same agent — not a conflict
                # Check line range overlap with tolerance
                if _ranges_overlap(
                    f1.line_start, f1.line_end,
                    f2.line_start, f2.line_end,
                    _OVERLAP_TOLERANCE,
                ):
                    overlapping.append(f2)

            # Only create a cluster if multiple agents are involved
            agents = set(f.agent for f in overlapping)
            if len(agents) >= 2:
                cluster_counter += 1
                # Compute cluster line range (union of all findings)
                line_start = min(f.line_start for f in overlapping)
                line_end = max(f.line_end for f in overlapping)

                cluster = ConflictCluster(
                    cluster_id=f"CC-{cluster_counter:03d}",
                    line_start=line_start,
                    line_end=line_end,
                    findings=overlapping,
                    max_rounds=settings.MAX_DEBATE_ROUNDS,
                )
                clusters.append(cluster)
                for f in overlapping:
                    used.add(f.finding_id)

        # Remaining un-clustered findings are "no conflict" — go straight to verdict
        unclustered = [f for f in findings if f.finding_id not in used]
        for f in unclustered:
            cluster_counter += 1
            clusters.append(ConflictCluster(
                cluster_id=f"CC-{cluster_counter:03d}",
                line_start=f.line_start,
                line_end=f.line_end,
                findings=[f],
                resolved=True,  # No debate needed
            ))

        logger.info(
            f"Conflict detection: {len(clusters)} clusters, "
            f"{sum(1 for c in clusters if c.has_conflict)} with active conflicts"
        )
        return clusters

    def _build_conflict_summary_entry(self) -> ProceedingEntry:
        """Build a proceeding entry summarizing the conflict detection results."""
        active = [c for c in self.conflict_clusters if c.has_conflict]
        resolved = [c for c in self.conflict_clusters if c.resolved]

        if not active:
            message = (
                f"Conflict detection complete. "
                f"{len(resolved)} findings with no conflict — proceeding to verdict. "
                f"No cross-examination required."
            )
        else:
            conflict_details = []
            for c in active:
                agents = ", ".join(c.agents_involved)
                conflict_details.append(
                    f"  {c.cluster_id}: lines {c.line_start}-{c.line_end} "
                    f"({agents} disagree)"
                )
            message = (
                f"Conflict detection complete. "
                f"{len(active)} conflicts found, {len(resolved)} uncontested. "
                f"Proceeding to cross-examination.\\n"
                + "\\n".join(conflict_details)
            )

        return ProceedingEntry(
            agent=AgentRole.ARBITER,
            tag="Conflict Analysis",
            message=message,
            round_number=0,
            timestamp=__import__("datetime").datetime.now(),
            confidence=1.0,
            phase=TrialPhase.CONFLICT_DETECTION,
            speaker="ARBITER",
        )

    # ═════════════════════════════════════════════════════════════════
    # Phase 3: Targeted Cross-Examination
    # ═════════════════════════════════════════════════════════════════

    async def _run_cross_examination(
        self, context: dict, active_clusters: List[ConflictCluster]
    ):
        """
        For each conflict cluster, call back ONLY the agents involved
        (not all 5 agents). Loop stops when:
        - An agent withdraws (confidence < 0.3)
        - Max rounds for cluster reached
        - Both sides maintain high confidence → mark as "disputed"
        """
        max_global_rounds = settings.MAX_DEBATE_ROUNDS

        for round_num in range(1, max_global_rounds + 1):
            context["current_round"] = round_num
            any_active = False

            for cluster in active_clusters:
                if cluster.resolved or cluster.debate_rounds >= cluster.max_rounds:
                    continue

                any_active = True
                cluster.debate_rounds += 1

                # Run cross-examination for each involved agent
                for agent_name in cluster.agents_involved:
                    role = _name_to_role(agent_name)
                    if role is None:
                        continue

                    # Update context with cluster info for the agent
                    context["conflict_clusters"] = self.conflict_clusters
                    context["current_cluster"] = cluster

                    entry = await self._run_agent_safe(role, context)
                    if entry is None:
                        return

                    yield entry

                    # Check if any agent withdrew (revised confidence below threshold)
                    if entry.findings:
                        for f in entry.findings:
                            matching = [
                                cf for cf in cluster.findings
                                if cf.finding_id == f.finding_id
                            ]
                            if matching and f.confidence < 0.3:
                                matching[0].withdrawn = True
                                matching[0].rebuttal = f.rebuttal or f.claim
                                logger.info(
                                    f"Agent {agent_name} withdrew finding "
                                    f"{f.finding_id} (confidence: {f.confidence})"
                                )

                    # Check resolution conditions
                    active_findings = [
                        f for f in cluster.findings if not f.withdrawn
                    ]
                    if len(active_findings) <= 1:
                        cluster.resolved = True
                        break

                # If both sides still have high confidence after max rounds,
                # mark as disputed (honest uncertainty)
                if cluster.debate_rounds >= cluster.max_rounds and not cluster.resolved:
                    active_findings = [
                        f for f in cluster.findings if not f.withdrawn
                    ]
                    if len(active_findings) >= 2:
                        high_conf = all(f.confidence >= 0.6 for f in active_findings)
                        if high_conf:
                            cluster.resolved = True
                            logger.info(
                                f"Cluster {cluster.cluster_id}: high-confidence "
                                f"disagreement — marking as disputed"
                            )

            if not any_active:
                break

    # ═════════════════════════════════════════════════════════════════
    # Helpers
    # ═════════════════════════════════════════════════════════════════

    def _build_context(self, code_content: str, language: str,
                       focus_area: str) -> dict:
        return {
            "code_content": code_content,
            "language": language,
            "focus_area": focus_area,
            "proceedings": self.proceedings,
            "current_round": 0,
            "token_usage": self.token_usage,
            "all_findings": self.all_findings,
            "conflict_clusters": self.conflict_clusters,
        }

    async def _run_agent(self, role: AgentRole,
                         context: dict) -> ProceedingEntry:
        entry = await self.agents[role].process(context)
        self.proceedings.append(entry)
        context["proceedings"] = self.proceedings
        # Collect findings from the entry
        if entry.findings:
            context.setdefault("all_findings", [])
            # Avoid duplicate findings
            existing_ids = {f.finding_id for f in context["all_findings"]}
            for f in entry.findings:
                if f.finding_id not in existing_ids:
                    context["all_findings"].append(f)
                    self.all_findings.append(f)
        return entry

    async def _run_agent_safe(self, role: AgentRole, context: dict):
        """Run an agent with cancellation guard."""
        if self._cancelled:
            logger.info(f"Skipping {role.value}: trial was cancelled.")
            return None

        self._current_task = asyncio.create_task(
            self._run_agent(role, context)
        )
        try:
            result = await self._current_task
            self._current_task = None
            return result
        except asyncio.CancelledError:
            logger.info(
                f"Cancelled during {role.value} API call. "
                f"In-flight request aborted, no tokens burned."
            )
            self._cancelled = True
            self._current_task = None
            return None

    def _emit_phase_banner(self, phase: str):
        """Yield a phase transition banner entry."""
        import datetime
        entry = ProceedingEntry(
            agent=AgentRole.ARBITER,
            tag="Phase Transition",
            message=f"Entering phase: {phase}",
            round_number=0,
            timestamp=datetime.datetime.now(),
            confidence=1.0,
            phase=phase,
            speaker="ARBITER",
        )
        self.proceedings.append(entry)
        yield entry

    def get_formatted_proceedings(self) -> str:
        """Return a human-readable transcript of all proceedings."""
        lines = []
        for e in self.proceedings:
            lines.append(
                f"[{e.timestamp.strftime('%H:%M:%S')}] "
                f"{e.agent.value} [{e.tag}, Round {e.round_number}]: {e.message}"
            )
        return "\n".join(lines)


# ── Utility functions ─────────────────────────────────────────────────

def _ranges_overlap(
    start1: int, end1: int,
    start2: int, end2: int,
    tolerance: int = 0,
) -> bool:
    """Check if two line ranges overlap within a tolerance."""
    return start1 <= end2 + tolerance and start2 <= end1 + tolerance


def _name_to_role(name: str) -> Optional[AgentRole]:
    """Map agent name string to AgentRole enum."""
    mapping = {
        "AEGIS": AgentRole.AEGIS,
        "AXIOM": AgentRole.AXIOM,
        "METRIC": AgentRole.METRIC,
        "ARBITER": AgentRole.ARBITER,
        "LEDGER": AgentRole.LEDGER,
    }
    return mapping.get(name.upper())
