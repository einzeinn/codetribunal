"""
CodeTribunal - Base Agent Module
Shared utilities, data models, and base class for all agents.

Includes structured finding models for the conditional multi-agent protocol:
- AgentFinding: Structured claim from an agent with line ranges and evidence
- ConflictCluster: Group of overlapping findings from different agents
- VerdictItem: Per-item ruling with reasoning trail
"""

import logging
from typing import Any, List, Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from openai import AsyncOpenAI
from ..config import settings

logger = logging.getLogger("codetribunal.agents")

# ── Shared Qwen client (OpenAI-compatible) ──────────────────────────
qwen_client = AsyncOpenAI(
    api_key=settings.QWEN_API_KEY,
    base_url=settings.QWEN_BASE_URL,
)

# ── Truncation constants ────────────────────────────────────────────
MAX_CODE_LINES = 400          # Max lines sent to LLM per agent
CODE_HEAD_LINES = 300         # First N lines (imports, class defs, most logic)
CODE_TAIL_LINES = 100         # Last N lines (entry points, main logic)
MAX_CODE_CHARS = 12000        # Max characters (backup cap)
MAX_TRANSCRIPT_CHARS = 4000   # Max transcript chars for context window
TRANSCRIPT_HEAD_CHARS = 2000  # Preserve early entries (LEDGER, AEGIS opening)
TRANSCRIPT_TAIL_CHARS = 2000  # Preserve recent entries (latest round)


# ── Truncation helpers ──────────────────────────────────────────────
def truncate_code(code: str, max_lines: int = MAX_CODE_LINES,
                  max_chars: int = MAX_CODE_CHARS) -> str:
    """
    Smart head+tail truncation for code.
    Preserves the beginning (imports, class/function signatures) and
    the end (main logic, entry points). Marks the gap explicitly so
    the LLM knows it's seeing an incomplete file.

    Strategy: first 300 lines + last 100 lines (within 400 total).
    Covers the vast majority of code review submissions in full.
    """
    if not code:
        return ""
    lines = code.split("\n")
    total = len(lines)

    if total <= max_lines:
        result = "\n".join(lines)
        if len(result) > max_chars:
            result = result[:max_chars]
        return result

    # Head + tail with explicit gap marker
    head = lines[:CODE_HEAD_LINES]
    tail = lines[-CODE_TAIL_LINES:]
    gap_start = CODE_HEAD_LINES + 1
    gap_end = total - CODE_TAIL_LINES
    skipped = gap_end - gap_start + 1

    parts = [
        "\n".join(head),
        f"\n# ... [{skipped} lines truncated (lines {gap_start}-{gap_end})] ...\n",
        "\n".join(tail),
    ]
    result = "\n".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars]
    return result


def truncate_transcript(transcript: str,
                        max_chars: int = MAX_TRANSCRIPT_CHARS) -> str:
    """
    Head+tail truncation for debate transcripts.
    Preserves the BEGINNING (LEDGER case filing, AEGIS opening statement)
    and the END (most recent round) so ARBITER has full context for verdict.

    Naive tail-only truncation would cause ARBITER to hallucinate
    without seeing the original accusations.
    """
    if not transcript or len(transcript) <= max_chars:
        return transcript

    head = transcript[:TRANSCRIPT_HEAD_CHARS]
    tail = transcript[-TRANSCRIPT_TAIL_CHARS:]

    return (
        f"{head}\n"
        f"[... middle proceedings condensed to preserve context window ...]\n"
        f"{tail}"
    )


# ── Token usage accumulator ─────────────────────────────────────────
@dataclass
class TokenUsageLog:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0

    def record(self, usage: Any):
        if usage:
            self.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.output_tokens += getattr(usage, "completion_tokens", 0) or 0
            self.calls += 1

    def summary(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "api_calls": self.calls,
        }


# ── Helper: call Qwen with error handling ───────────────────────────
async def call_qwen(
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float = 0.7,
    max_tokens: int = 1500,
) -> tuple[str, Any]:
    """Call Qwen API and return (content, usage)."""
    try:
        response = await qwen_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content.strip()
        usage = response.usage
        return content, usage
    except Exception as e:
        logger.error(f"Qwen API call failed (model={model}): {e}")
        raise


# ── Structured Finding Models (Conditional Debate Protocol) ─────────

@dataclass
class AgentFinding:
    """
    A structured finding from an agent with line ranges and tool evidence.
    Replaces free-text claims with machine-comparable data for conflict detection.
    """
    finding_id: str              # e.g. "AEGIS-F001", "METRIC-F001"
    agent: str                   # "AEGIS", "AXIOM", "METRIC"
    category: str                # "security", "complexity", "maintainability", "validation"
    severity: str                # "critical", "high", "medium", "low", "info"
    line_start: int              # 1-based start line
    line_end: int                # 1-based end line
    claim: str                   # The agent's claim about this code region
    evidence_source: str = ""    # Tool that produced this (e.g. "bandit:B608", "radon:CC")
    confidence: float = 0.8     # Agent's confidence in this finding
    tool_data: Dict[str, Any] = field(default_factory=dict)  # Raw tool output
    rebuttal: Optional[str] = None  # Filled during cross-examination
    withdrawn: bool = False      # Set True if agent revises confidence below threshold

    @property
    def line_range(self) -> tuple:
        return (self.line_start, self.line_end)

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "agent": self.agent,
            "category": self.category,
            "severity": self.severity,
            "line_range": [self.line_start, self.line_end],
            "claim": self.claim,
            "evidence_source": self.evidence_source,
            "confidence": self.confidence,
            "withdrawn": self.withdrawn,
        }


@dataclass
class ConflictCluster:
    """
    A group of findings from different agents that overlap on the same
    code region but reach different conclusions. Only these go to debate.
    """
    cluster_id: str                          # e.g. "CC-001"
    line_start: int
    line_end: int
    findings: List[AgentFinding] = field(default_factory=list)
    debate_rounds: int = 0                   # How many cross-exam rounds done
    max_rounds: int = 2                      # Max rounds for this cluster
    resolved: bool = False

    @property
    def agents_involved(self) -> List[str]:
        return list(set(f.agent for f in self.findings if not f.withdrawn))

    @property
    def has_conflict(self) -> bool:
        """True if non-withdrawn findings disagree on severity or conclusion."""
        active = [f for f in self.findings if not f.withdrawn]
        if len(active) <= 1:
            return False
        severities = set(f.severity for f in active)
        return len(severities) > 1 or any(
            "objection" in f.claim.lower() or "disagree" in f.claim.lower()
            for f in active
        )

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "line_range": [self.line_start, self.line_end],
            "findings": [f.to_dict() for f in self.findings],
            "debate_rounds": self.debate_rounds,
            "resolved": self.resolved,
            "agents_involved": self.agents_involved,
        }


@dataclass
class VerdictItem:
    """
    Per-item verdict from ARBITER. Each finding/cluster gets its own ruling.
    """
    item_id: str                    # Links to finding_id or cluster_id
    status: str                     # "confirmed", "dismissed", "disputed"
    severity: str                   # Final severity ruling
    reasoning: str                  # ARBITER's reasoning
    recommendation: str = ""       # Fix recommendation
    confidence: float = 0.8
    evidence_trail: List[str] = field(default_factory=list)  # Which arguments won

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "status": self.status,
            "severity": self.severity,
            "reasoning": self.reasoning,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "evidence_trail": self.evidence_trail,
        }


class TrialPhase:
    """Tracks the current phase of the trial for frontend state."""
    INVESTIGATION = "investigation"      # Parallel agent scanning
    CONFLICT_DETECTION = "conflict_detection"  # Deterministic comparison
    CROSS_EXAMINATION = "cross_examination"   # Targeted debate
    VERDICT = "verdict"                  # Final rulings
    COMPLETE = "complete"


# ── Data models ─────────────────────────────────────────────────────
class AgentRole(Enum):
    LEDGER = "LEDGER"
    AEGIS = "AEGIS"
    AXIOM = "AXIOM"
    METRIC = "METRIC"
    ARBITER = "ARBITER"


@dataclass
class ProceedingEntry:
    agent: AgentRole
    tag: str
    message: str
    round_number: int
    timestamp: datetime
    confidence: float = 1.0
    # Structured metadata for frontend rendering
    phase: str = ""                          # TrialPhase value
    speaker: str = ""                        # Active speaker agent
    exhibit_ref: str = ""                    # Code exhibit reference (e.g. "Exhibit A")
    is_objection: bool = False               # Trigger objection animation
    findings: List[AgentFinding] = field(default_factory=list)  # Structured findings
    line_range: Optional[List[int]] = None   # [start, end] for exhibit highlighting
    rubric_scores: Optional[Dict[str, Any]] = None  # Deterministic scores from rubric


# ── Base Agent ──────────────────────────────────────────────────────
class BaseAgent:
    def __init__(self, role: AgentRole, model_name: str, system_prompt: str):
        self.role = role
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.name = role.value

    async def process(self, context: dict) -> ProceedingEntry:
        raise NotImplementedError

    async def _call_llm(self, user_content: str,
                        temperature: float = 0.7,
                        max_tokens: int = 1500) -> tuple[str, Any]:
        return await call_qwen(
            self.model_name, self.system_prompt,
            user_content, temperature, max_tokens,
        )

    def _entry(self, tag: str, message: str,
               round_num: int, confidence: float = 1.0,
               phase: str = "", speaker: str = "",
               exhibit_ref: str = "", is_objection: bool = False,
               findings: Optional[List] = None,
               line_range: Optional[List[int]] = None,
               rubric_scores: Optional[Dict[str, Any]] = None) -> ProceedingEntry:
        return ProceedingEntry(
            agent=self.role, tag=tag, message=message,
            round_number=round_num, timestamp=datetime.now(),
            confidence=confidence, phase=phase, speaker=speaker,
            exhibit_ref=exhibit_ref, is_objection=is_objection,
            findings=findings or [], line_range=line_range,
            rubric_scores=rubric_scores,
        )


# ── Transcript builder ──────────────────────────────────────────────
def build_transcript(context: dict) -> str:
    """Build a readable transcript from proceedings list for LLM context."""
    proceedings: List[ProceedingEntry] = context.get("proceedings", [])
    if not proceedings:
        return ""
    lines = []
    for p in proceedings:
        lines.append(
            f"[{p.agent.value}] ({p.tag}, Round {p.round_number}): {p.message}"
        )
    return "\n".join(lines)


# ── Cluster history builder ────────────────────────────────────────
def build_cluster_history(
    clusters: List[ConflictCluster],
    agent_name: str = "",
) -> str:
    """
    Build a structured per-cluster debate history.
    If agent_name is given, only return history for clusters involving that agent.
    This replaces raw transcript dumping with targeted, structured state passing.
    """
    if not clusters:
        return ""

    relevant = clusters
    if agent_name:
        relevant = [
            c for c in clusters
            if agent_name in [f.agent for f in c.findings]
        ]

    if not relevant:
        return ""

    parts = ["DEBATE HISTORY (structured per-cluster):"]
    for c in relevant:
        state = "RESOLVED" if c.resolved else (
            "DISPUTED" if c.has_conflict else "UNCONTESTED"
        )
        parts.append(
            f"\n  Cluster {c.cluster_id} (lines {c.line_start}-{c.line_end}) "
            f"— {state}, {c.debate_rounds} rounds"
        )

        # Group findings by agent for clarity
        by_agent: Dict[str, list] = {}
        for f in c.findings:
            by_agent.setdefault(f.agent, []).append(f)

        for ag, findings in by_agent.items():
            parts.append(f"    {ag}:")
            for f in findings:
                status = " [WITHDRAWN]" if f.withdrawn else ""
                rebuttal = f" — rebuttal: {f.rebuttal[:80]}" if f.rebuttal else ""
                parts.append(
                    f"      {f.finding_id}: [{f.severity}] {f.claim[:100]} "
                    f"(confidence: {f.confidence}{status}){rebuttal}"
                )

    return "\n".join(parts)
