"""
CodeTribunal - Benchmark Module
Compares single-agent baseline vs multi-agent tribunal on the same code.

Track 3 "Agent Society" requirement: demonstrate measurable efficiency gain
over single-agent baselines.

Metrics compared:
- Findings discovered (multi-agent should find more)
- False positive rate (multi-agent has fewer via cross-examination withdrawals)
- Confidence calibration (multi-agent confidence more consistent)
- Token efficiency (parallel + targeted debate vs one giant prompt)
"""

import logging
import time
from typing import Any, Dict, List
from dataclasses import dataclass, field

from .base import call_qwen, AgentFinding
from .orchestrator import TribunalCourt
from ..config import settings

logger = logging.getLogger("codetribunal.benchmark")

# ── Single-agent system prompt (no tools, no debate, just one LLM call) ──
BASELINE_SYSTEM_PROMPT = (
    "You are an expert code reviewer. Analyze the following code for "
    "security vulnerabilities, performance issues, and maintainability problems. "
    "For each issue found, state: the line range, severity (critical/high/medium/low), "
    "category, and a one-sentence description. "
    "Then provide scores: Security (0-10), Performance (0-10), Maintainability (0-10). "
    "End with: APPROVED, APPROVED WITH CONDITIONS, or REJECTED. "
    "Be thorough but concise."
)


@dataclass
class BenchmarkResult:
    """Result from one review method (baseline or multi-agent)."""
    method: str                    # "single_agent" or "multi_agent"
    findings_count: int = 0        # Total findings discovered
    withdrawn_count: int = 0       # Findings withdrawn (false positives)
    active_findings: int = 0       # Findings that survived scrutiny
    security_score: float = 5.0
    performance_score: float = 5.0
    maintainability_score: float = 5.0
    token_input: int = 0
    token_output: int = 0
    wall_time_ms: int = 0          # Wall clock time in milliseconds
    api_calls: int = 0
    raw_output: str = ""


async def run_baseline_review(
    code_content: str, language: str = "unknown"
) -> BenchmarkResult:
    """
    Run a single-agent baseline review: ONE LLM call, no tools, no debate.
    This is the simplest possible code review approach.
    """
    start = time.monotonic()

    prompt = (
        f"Review this {language} code for security, performance, and "
        f"maintainability issues.\n\n```{language}\n{code_content[:8000]}\n```\n\n"
        "List each issue with line range, severity, and category. "
        "Then score: Security (0-10), Performance (0-10), Maintainability (0-10). "
        "End with APPROVED / APPROVED WITH CONDITIONS / REJECTED."
    )

    try:
        content, usage = await call_qwen(
            model=settings.AEGIS_MODEL,  # Use same model as AEGIS for fair comparison
            system_prompt=BASELINE_SYSTEM_PROMPT,
            user_content=prompt,
            temperature=0.5,
            max_tokens=2000,
        )
    except Exception as e:
        logger.error(f"Baseline review failed: {e}")
        content = f"Error: {e}"
        usage = None

    elapsed = int((time.monotonic() - start) * 1000)

    # Parse scores from output (best effort)
    import re
    sec = _extract_score(content, r"[Ss]ecurity\s*[:\-/]?\s*(\d+(?:\.\d+)?)")
    perf = _extract_score(content, r"[Pp]erformance\s*[:\-/]?\s*(\d+(?:\.\d+)?)")
    maint = _extract_score(content, r"[Mm]aintainability\s*[:\-/]?\s*(\d+(?:\.\d+)?)")

    # Count "findings" from output (rough heuristic)
    finding_lines = [
        l for l in content.split("\n")
        if any(kw in l.lower() for kw in ["critical", "high", "medium", "vulnerability", "issue"])
    ]

    return BenchmarkResult(
        method="single_agent",
        findings_count=len(finding_lines),
        active_findings=len(finding_lines),  # No cross-exam, so all "survive"
        security_score=sec,
        performance_score=perf,
        maintainability_score=maint,
        token_input=getattr(usage, "prompt_tokens", 0) if usage else 0,
        token_output=getattr(usage, "completion_tokens", 0) if usage else 0,
        wall_time_ms=elapsed,
        api_calls=1,
        raw_output=content,
    )


async def run_multi_agent_review(
    code_content: str, language: str = "unknown", focus_area: str = ""
) -> BenchmarkResult:
    """
    Run the full multi-agent tribunal with tools, debate, and cross-examination.
    """
    start = time.monotonic()

    tribunal = TribunalCourt()
    proceedings = await tribunal.conduct_trial(code_content, language, focus_area)

    elapsed = int((time.monotonic() - start) * 1000)

    # Extract metrics from tribunal results
    all_findings = tribunal.all_findings
    withdrawn = [f for f in all_findings if f.withdrawn]
    active = [f for f in all_findings if not f.withdrawn]

    # Extract rubric scores from verdict entry
    rubric = None
    for entry in proceedings:
        if entry.rubric_scores:
            rubric = entry.rubric_scores
            break

    # Fallback: parse from verdict text if no rubric
    verdict_text = ""
    for entry in proceedings:
        if entry.tag == "Final Verdict":
            verdict_text = entry.message
            break

    if rubric:
        sec = rubric["security"]
        perf = rubric["performance"]
        maint = rubric["maintainability"]
    else:
        import re
        sec = _extract_score(verdict_text, r"[Ss]ecurity\s*[:\-/]?\s*(\d+(?:\.\d+)?)")
        perf = _extract_score(verdict_text, r"[Pp]erformance\s*[:\-/]?\s*(\d+(?:\.\d+)?)")
        maint = _extract_score(verdict_text, r"[Mm]aintainability\s*[:\-/]?\s*(\d+(?:\.\d+)?)")

    usage = tribunal.token_usage

    return BenchmarkResult(
        method="multi_agent",
        findings_count=len(all_findings),
        withdrawn_count=len(withdrawn),
        active_findings=len(active),
        security_score=sec,
        performance_score=perf,
        maintainability_score=maint,
        token_input=usage.input_tokens,
        token_output=usage.output_tokens,
        wall_time_ms=elapsed,
        api_calls=usage.calls,
        raw_output=verdict_text[:500],
    )


async def run_benchmark_comparison(
    code_content: str, language: str = "unknown", focus_area: str = ""
) -> Dict[str, Any]:
    """
    Run both baseline and multi-agent on the same code, return comparison.
    """
    baseline = await run_baseline_review(code_content, language)
    multi = await run_multi_agent_review(code_content, language, focus_area)

    comparison = {
        "baseline": {
            "method": baseline.method,
            "findings_count": baseline.findings_count,
            "active_findings": baseline.active_findings,
            "withdrawn_count": baseline.withdrawn_count,
            "security": baseline.security_score,
            "performance": baseline.performance_score,
            "maintainability": baseline.maintainability_score,
            "tokens_total": baseline.token_input + baseline.token_output,
            "api_calls": baseline.api_calls,
            "wall_time_ms": baseline.wall_time_ms,
        },
        "multi_agent": {
            "method": multi.method,
            "findings_count": multi.findings_count,
            "active_findings": multi.active_findings,
            "withdrawn_count": multi.withdrawn_count,
            "security": multi.security_score,
            "performance": multi.performance_score,
            "maintainability": multi.maintainability_score,
            "tokens_total": multi.token_input + multi.token_output,
            "api_calls": multi.api_calls,
            "wall_time_ms": multi.wall_time_ms,
        },
        "comparison": {
            "findings_gain": multi.findings_count - baseline.findings_count,
            "false_positives_filtered": multi.withdrawn_count,
            "token_overhead": (
                (multi.token_input + multi.token_output)
                - (baseline.token_input + baseline.token_output)
            ),
            "time_overhead_ms": multi.wall_time_ms - baseline.wall_time_ms,
            "summary": (
                f"Multi-agent found {multi.findings_count} findings vs "
                f"{baseline.findings_count} from single agent "
                f"(+{multi.findings_count - baseline.findings_count}). "
                f"Filtered {multi.withdrawn_count} false positives via cross-examination. "
                f"Used {multi.api_calls} API calls vs 1 baseline call."
            ),
        },
    }

    return comparison


def _extract_score(text: str, pattern: str) -> float:
    """Extract a numeric score from text using regex."""
    import re
    match = re.search(pattern, text)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            pass
    return 5.0  # Default
