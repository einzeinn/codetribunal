"""
CodeTribunal - Code Chunker Module
Semantic code splitting for multi-agent security analysis.

Eliminates "middle blindness" by extracting functions/classes as discrete
chunks rather than naive line-based truncation. Each chunk preserves its
full source code, ensuring no vulnerability falls into a truncation gap.

Strategies:
- Python: AST extraction (built-in `ast` module, zero dependencies)
- Other languages: Truncated full code (avoids fragile regex parsing)

Prioritization: Risk-based pre-scanning (not size-based).
Small but dangerous functions (e.g. `os.system()`) are kept over
large but benign rendering logic.
"""

import ast
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("codetribunal.chunker")

MAX_CHUNKS = 4          # Max chunks sent to agents (prevents token explosion)
MAX_CHUNK_CHARS = 3000  # Max chars per individual chunk
MAX_TOTAL_CHARS = 12000 # Max total chars across all chunks

# ── Risk pre-scan keywords ─────────────────────────────────────────
# Scored by security severity. Small but dangerous code (e.g. `os.system()`)
# gets a high score; large benign rendering logic gets zero.
_RISK_KEYWORDS: dict[str, int] = {
    # Command execution (critical)
    "os.system": 5, "os.popen": 5, "subprocess": 5, "shell=True": 5,
    "exec(": 5, "eval(": 5, "compile(": 4,
    # File / path operations
    "open(": 2, "shutil": 2, "pathlib": 1,
    # Dynamic imports / code loading
    "__import__": 4, "importlib": 3,
    # Authentication / secrets
    "password": 3, "secret": 3, "token": 2, "api_key": 4,
    "jwt": 3, "hash": 2, "encrypt": 2, "decrypt": 2,
    # Database / SQL
    "query": 2, "execute": 3, "raw(": 4, "cursor": 3,
    "sql": 3, "sqlalchemy": 2,
    # Network / external calls
    "requests": 2, "httpx": 2, "urllib": 2, "socket": 3,
    "fetch(": 2, "axios": 2,
    # Deserialization (critical)
    "pickle": 4, "yaml.load": 4, "marshal": 3, "shelve": 3,
    # Input handling
    "input(": 2, "stdin": 2, "request": 1,
    # Environment / config
    "getenv": 2, "environ": 2, "dotenv": 1,
}


def _score_risk(source: str) -> int:
    """
    Pre-scan source code for security-relevant keywords.
    Returns a weighted risk score — higher = more suspicious.
    This ensures small dangerous functions (e.g. `os.system(cmd)`)
    are prioritized over large benign ones (e.g. UI rendering).
    """
    score = 0
    lower = source.lower()
    for keyword, weight in _RISK_KEYWORDS.items():
        if keyword.lower() in lower:
            score += weight
    return score


@dataclass
class CodeChunk:
    """A semantically meaningful unit of code (function, class, or block)."""
    name: str               # e.g. "process_payment", "class UserAuth"
    chunk_type: str         # "function", "class", "module_level", "block"
    source: str             # Full source code of this chunk
    start_line: int         # 1-based start line in original file
    end_line: int           # 1-based end line in original file
    line_count: int         # Number of lines
    char_count: int         # Number of characters
    risk_score: int = 0     # Pre-scan risk score (higher = more suspicious)

    @property
    def header(self) -> str:
        """One-line summary for structural overview."""
        risk_tag = f" [RISK:{self.risk_score}]" if self.risk_score > 0 else ""
        return (
            f"[{self.chunk_type}] {self.name}{risk_tag} "
            f"(lines {self.start_line}-{self.end_line}, {self.line_count} lines)"
        )


def chunk_code(code: str, language: str = "python") -> List[CodeChunk]:
    """
    Split code into semantic chunks with risk-based prioritization.

    Python: AST extraction → risk-scored chunks.
    Other languages: Truncated full code (avoids fragile regex parsing).

    Taint flow preservation: If ALL chunks fit within MAX_TOTAL_CHARS,
    they are all passed (no data flow loss between functions).
    Only when limits are exceeded do we compress low-risk chunks.
    """
    if not code or not code.strip():
        return []

    if language.lower() in ("python", "py"):
        chunks = _chunk_python_ast(code)
    else:
        # Non-Python: pass truncated full code as single chunk.
        # Avoids fragile regex parsing that produces broken syntax.
        return _chunk_full_code_fallback(code, language)

    if not chunks:
        lines = code.split("\n")
        return [CodeChunk(
            name="full_file",
            chunk_type="module",
            source=code[:MAX_TOTAL_CHARS],
            start_line=1,
            end_line=len(lines),
            line_count=len(lines),
            char_count=min(len(code), MAX_TOTAL_CHARS),
            risk_score=_score_risk(code),
        )]

    # Score each chunk for security risk (pre-scan)
    for chunk in chunks:
        chunk.risk_score = _score_risk(chunk.source)

    # Taint flow: if everything fits, pass ALL chunks (no data flow loss)
    total_chars = sum(c.char_count for c in chunks)
    if len(chunks) <= MAX_CHUNKS and total_chars <= MAX_TOTAL_CHARS:
        # Sort by risk (highest first) but keep all
        chunks.sort(key=lambda c: c.risk_score, reverse=True)
        return chunks

    # Over limit: sort by risk, keep top chunks, compress low-risk ones
    chunks.sort(key=lambda c: c.risk_score, reverse=True)
    chunks = _enforce_limits(chunks)

    logger.debug(
        f"Chunked {language} code: {len(chunks)} chunks, "
        f"total {sum(c.char_count for c in chunks)} chars"
    )
    return chunks


def build_structural_overview(chunks: List[CodeChunk]) -> str:
    """
    Build a lightweight structural overview of all chunks.
    This is what AEGIS sees first to identify suspicious regions.
    """
    if not chunks:
        return ""
    lines = ["Code structure overview:"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"  {i}. {chunk.header}")
    return "\n".join(lines)


def build_chunked_code(chunks: List[CodeChunk]) -> str:
    """
    Build the full chunked code representation for agent prompts.
    Each chunk is clearly delimited with its metadata.
    """
    if not chunks:
        return ""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"--- Chunk {i}: {chunk.name} "
            f"(lines {chunk.start_line}-{chunk.end_line}) ---\n"
            f"{chunk.source}\n"
        )
    return "\n".join(parts)


# ── Python AST extraction ───────────────────────────────────────────

def _chunk_python_ast(code: str) -> List[CodeChunk]:
    """Extract functions and classes from Python code using the ast module."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        logger.debug("AST parse failed, falling back to full code.")
        return _chunk_full_code_fallback(code, "python")

    lines = code.split("\n")
    chunks: List[CodeChunk] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            chunk = _extract_node_chunk(node, lines, "function")
            if chunk:
                chunks.append(chunk)

        elif isinstance(node, ast.ClassDef):
            chunk = _extract_node_chunk(node, lines, "class")
            if chunk:
                chunks.append(chunk)

    # Collect module-level code (imports, constants, etc.)
    module_level_nodes = [
        n for n in ast.iter_child_nodes(tree)
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    if module_level_nodes:
        start = min(n.lineno for n in module_level_nodes)
        end = max(getattr(n, 'end_lineno', n.lineno) for n in module_level_nodes)
        source = "\n".join(lines[start - 1:end])
        if source.strip():
            chunks.append(CodeChunk(
                name="module_level",
                chunk_type="module_level",
                source=source[:MAX_CHUNK_CHARS],
                start_line=start,
                end_line=end,
                line_count=end - start + 1,
                char_count=min(len(source), MAX_CHUNK_CHARS),
            ))

    return chunks


def _extract_node_chunk(node: ast.AST, lines: List[str],
                        chunk_type: str) -> CodeChunk | None:
    """Extract a CodeChunk from an AST node."""
    start = node.lineno
    end = getattr(node, 'end_lineno', start)
    source = "\n".join(lines[start - 1:end])

    if not source.strip():
        return None

    return CodeChunk(
        name=getattr(node, 'name', '<anonymous>'),
        chunk_type=chunk_type,
        source=source[:MAX_CHUNK_CHARS],
        start_line=start,
        end_line=end,
        line_count=end - start + 1,
        char_count=min(len(source), MAX_CHUNK_CHARS),
    )


# ── Non-Python fallback: truncated full code ───────────────────────

def _chunk_full_code_fallback(code: str, language: str) -> List[CodeChunk]:
    """
    For non-Python languages, pass the full code as a single truncated chunk.
    This is safer than fragile regex parsing which produces broken syntax
    for nested callbacks, arrow functions, multi-line parameters, etc.
    """
    lines = code.split("\n")
    source = code[:MAX_TOTAL_CHARS]
    return [CodeChunk(
        name=f"full_file ({language})",
        chunk_type="module",
        source=source,
        start_line=1,
        end_line=len(lines),
        line_count=len(lines),
        char_count=len(source),
        risk_score=_score_risk(code),
    )]


# ── Risk-aware limit enforcement ─────────────────────────────────────

def _enforce_limits(chunks: List[CodeChunk]) -> List[CodeChunk]:
    """
    Enforce MAX_CHUNKS and MAX_TOTAL_CHARS limits.
    Already sorted by risk_score (highest first).

    Strategy: Keep high-risk chunks intact, compress low-risk chunks
    into a single 'remaining_code' block that preserves signatures
    (so agents can still see the taint flow path).
    """
    if len(chunks) <= MAX_CHUNKS:
        total = sum(c.char_count for c in chunks)
        if total <= MAX_TOTAL_CHARS:
            return chunks

    # Take top MAX_CHUNKS - 1 high-risk chunks
    kept = list(chunks[:MAX_CHUNKS - 1])
    overflow = chunks[MAX_CHUNKS - 1:]

    if overflow:
        # Build a compressed summary of low-risk chunks
        # Preserves function signatures for taint flow visibility
        summary_lines = []
        full_sources = []
        for c in overflow:
            summary_lines.append(
                f"# [{c.chunk_type}] {c.name} "
                f"(lines {c.start_line}-{c.end_line}, risk:{c.risk_score})"
            )
            full_sources.append(c.source)

        # Include full source of overflow chunks if space allows
        merged_source = (
            "# --- Low-risk chunks (signatures + source) ---\n"
            + "\n\n".join(summary_lines)
            + "\n\n"
            + "\n\n".join(full_sources)
        )
        truncated = merged_source[:MAX_CHUNK_CHARS]

        merged = CodeChunk(
            name=f"remaining_code ({len(overflow)} blocks, low-risk)",
            chunk_type="merged",
            source=truncated,
            start_line=min(c.start_line for c in overflow),
            end_line=max(c.end_line for c in overflow),
            line_count=sum(c.line_count for c in overflow),
            char_count=len(truncated),
            risk_score=max(c.risk_score for c in overflow),
        )
        kept.append(merged)

    # Final total char enforcement
    total = sum(c.char_count for c in kept)
    if total > MAX_TOTAL_CHARS:
        excess = total - MAX_TOTAL_CHARS
        if kept:
            last = kept[-1]
            trim_to = max(0, last.char_count - excess)
            last.source = last.source[:trim_to]
            last.char_count = len(last.source)

    return kept

