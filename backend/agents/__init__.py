"""
CodeTribunal - Agents Package

Five officers of the court:
- LEDGER: Clerk (AST structural parsing)
- AEGIS: Prosecutor (bandit security scanning + LLM reasoning)
- AXIOM: Defense Attorney (validation pattern detection + LLM reasoning)
- METRIC: Expert Witness (radon complexity analysis + LLM reasoning)
- ARBITER: Judge (per-item verdict with reasoning trail)
"""

from .base import (
    TokenUsageLog,
    AgentRole,
    ProceedingEntry,
    AgentFinding,
    ConflictCluster,
    VerdictItem,
    TrialPhase,
    BaseAgent,
    call_qwen,
    qwen_client,
    truncate_code,
    truncate_transcript,
    MAX_CODE_LINES,
    MAX_CODE_CHARS,
    MAX_TRANSCRIPT_CHARS,
    CODE_HEAD_LINES,
    CODE_TAIL_LINES,
)
from .ledger import LedgerAgent
from .aegis import AegisAgent
from .axiom import AxiomAgent
from .metric import MetricAgent
from .arbiter import ArbiterAgent
from .orchestrator import TribunalCourt
from .code_chunker import (
    CodeChunk,
    chunk_code,
    build_structural_overview,
    build_chunked_code,
    MAX_CHUNKS,
)
from .tools import (
    ToolFinding,
    StructuralIndex,
    ValidationPattern,
    BanditRunner,
    RadonRunner,
    ASTParser,
    ValidationDetector,
)

__all__ = [
    "TokenUsageLog",
    "AgentRole",
    "ProceedingEntry",
    "AgentFinding",
    "ConflictCluster",
    "VerdictItem",
    "TrialPhase",
    "BaseAgent",
    "call_qwen",
    "qwen_client",
    "truncate_code",
    "truncate_transcript",
    "CODE_HEAD_LINES",
    "CODE_TAIL_LINES",
    "LedgerAgent",
    "AegisAgent",
    "AxiomAgent",
    "MetricAgent",
    "ArbiterAgent",
    "TribunalCourt",
    "CodeChunk",
    "chunk_code",
    "build_structural_overview",
    "build_chunked_code",
    "MAX_CHUNKS",
    "ToolFinding",
    "StructuralIndex",
    "ValidationPattern",
    "BanditRunner",
    "RadonRunner",
    "ASTParser",
    "ValidationDetector",
]
"""
CodeTribunal - Agents Package

Five officers of the court:
- LEDGER: Clerk (recording/parsing)
- AEGIS: Prosecutor (security vulnerabilities)
- AXIOM: Defense Attorney (counter-arguments)
- METRIC: Expert Witness (performance metrics)
- ARBITER: Judge (orchestrator & verdict)
"""

from .base import (
    TokenUsageLog,
    AgentRole,
    ProceedingEntry,
    BaseAgent,
    call_qwen,
    qwen_client,
    truncate_code,
    truncate_transcript,
    MAX_CODE_LINES,
    MAX_CODE_CHARS,
    MAX_TRANSCRIPT_CHARS,
    CODE_HEAD_LINES,
    CODE_TAIL_LINES,
)
from .ledger import LedgerAgent
from .aegis import AegisAgent
from .axiom import AxiomAgent
from .metric import MetricAgent
from .arbiter import ArbiterAgent
from .orchestrator import TribunalCourt
from .code_chunker import (
    CodeChunk,
    chunk_code,
    build_structural_overview,
    build_chunked_code,
    MAX_CHUNKS,
)

__all__ = [
    "TokenUsageLog",
    "AgentRole",
    "ProceedingEntry",
    "BaseAgent",
    "call_qwen",
    "qwen_client",
    "truncate_code",
    "truncate_transcript",
    "CODE_HEAD_LINES",
    "CODE_TAIL_LINES",
    "LedgerAgent",
    "AegisAgent",
    "AxiomAgent",
    "MetricAgent",
    "ArbiterAgent",
    "TribunalCourt",
    "CodeChunk",
    "chunk_code",
    "build_structural_overview",
    "build_chunked_code",
    "MAX_CHUNKS",
]
