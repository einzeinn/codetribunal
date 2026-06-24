"""
CodeTribunal - Tool Access Layer
Real tool integrations for evidence-based agent findings.

Each tool returns structured data that agents incorporate into their
arguments, replacing pure-LLM guessing with actual tool evidence.

Tools:
- BanditRunner: Security linting (AEGIS evidence)
- RadonRunner: Complexity metrics (METRIC evidence)
- ASTParser: Structural indexing (LEDGER case file)
- ValidationDetector: Finds sanitization/validation patterns (AXIOM defense evidence)
"""

import ast
import json
import logging
import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger("codetribunal.tools")

# Use the current Python interpreter for subprocess tool calls
# This ensures bandit/radon are found in the active venv
_PYTHON = sys.executable


# ── Data Models ────────────────────────────────────────────────────────

@dataclass
class ToolFinding:
    """A single finding from a real tool (bandit, radon, etc.)."""
    tool_name: str          # "bandit", "radon", "ast", "validator"
    rule_id: str            # e.g. "B608", "C901", "hardcoded_password"
    category: str           # "security", "complexity", "structure", "validation"
    severity: str           # "critical", "high", "medium", "low", "info"
    line_start: int         # 1-based
    line_end: int           # 1-based
    message: str            # Human-readable finding description
    evidence: str = ""      # Raw tool output / code snippet
    confidence: float = 0.9 # Tool-derived confidence


@dataclass
class StructuralIndex:
    """LEDGER's indexed view of code structure from AST parsing."""
    functions: List[Dict[str, Any]] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0


@dataclass
class ValidationPattern:
    """A detected validation/sanitization pattern (AXIOM defense evidence)."""
    pattern_type: str       # "input_validation", "sanitization", "parameterized_query", etc.
    line_start: int
    line_end: int
    description: str
    protects_against: List[str] = field(default_factory=list)


# ── Bandit Runner (Security Linting for AEGIS) ────────────────────────

class BanditRunner:
    """
    Runs bandit security linter on Python code.
    Returns structured findings with real rule IDs (B608, B104, etc.).
    """

    @staticmethod
    def is_available() -> bool:
        try:
            result = subprocess.run(
                [_PYTHON, "-m", "bandit", "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def run(code: str) -> List[ToolFinding]:
        """Run bandit on code and return structured findings."""
        if not code.strip():
            return []

        findings = []
        tmp_file = None
        try:
            # Write code to temp file for bandit to analyze
            tmp_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, encoding='utf-8'
            )
            tmp_file.write(code)
            tmp_file.flush()
            tmp_file.close()

            result = subprocess.run(
                [_PYTHON, "-m", "bandit", "-f", "json", "-q", tmp_file.name],
                capture_output=True, text=True, timeout=30
            )

            # Bandit exits 0 if no issues, 1 if issues found
            if result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    for issue in data.get("results", []):
                        severity_map = {
                            "HIGH": "high", "MEDIUM": "medium", "LOW": "low"
                        }
                        # Bandit's end_col_offset is a COLUMN offset, not a line number.
                        # Use line_number for both start and end (single-line finding).
                        # For multi-line issues, estimate end from code context.
                        start_line = issue.get("line_number", 0)
                        # Estimate end line: most bandit findings are single-line.
                        # For multi-line (e.g., SQL strings), add a small buffer.
                        end_line = start_line
                        code_snippet = issue.get("code", "")
                        if code_snippet and "\n" in code_snippet:
                            end_line = start_line + code_snippet.count("\n")

                        findings.append(ToolFinding(
                            tool_name="bandit",
                            rule_id=issue.get("test_id", "unknown"),
                            category="security",
                            severity=severity_map.get(
                                issue.get("issue_severity", "MEDIUM"), "medium"
                            ),
                            line_start=start_line,
                            line_end=end_line,
                            message=issue.get("issue_text", ""),
                            evidence=f"Rule: {issue.get('test_id', '?')} "
                                     f"({issue.get('test_name', '?')}) — "
                                     f"Confidence: {issue.get('issue_confidence', '?')}",
                            confidence=_bandit_confidence(
                                issue.get("issue_confidence", "MEDIUM")
                            ),
                        ))
                except json.JSONDecodeError:
                    logger.warning("Bandit output was not valid JSON")

        except FileNotFoundError:
            logger.warning("Bandit not installed — skipping security linting")
        except subprocess.TimeoutExpired:
            logger.warning("Bandit timed out after 30s")
        except Exception as e:
            logger.warning(f"Bandit run failed: {e}")
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass

        return findings


def _bandit_confidence(conf: str) -> float:
    return {"HIGH": 0.9, "MEDIUM": 0.7, "LOW": 0.5}.get(conf.upper(), 0.6)


# ── Radon Runner (Complexity Metrics for METRIC) ──────────────────────

class RadonRunner:
    """
    Runs radon for cyclomatic complexity and maintainability index.
    Returns real numeric metrics instead of LLM-estimated ones.
    """

    @staticmethod
    def is_available() -> bool:
        try:
            result = subprocess.run(
                [_PYTHON, "-m", "radon", "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def run(code: str) -> List[ToolFinding]:
        """Run radon complexity + maintainability analysis."""
        if not code.strip():
            return []

        findings = []
        tmp_file = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, encoding='utf-8'
            )
            tmp_file.write(code)
            tmp_file.flush()
            tmp_file.close()

            # Cyclomatic complexity (cc)
            cc_result = subprocess.run(
                [_PYTHON, "-m", "radon", "cc", "-j", "-s", tmp_file.name],
                capture_output=True, text=True, timeout=30
            )
            if cc_result.stdout.strip():
                try:
                    cc_data = json.loads(cc_result.stdout)
                    for file_path, blocks in cc_data.items():
                        if isinstance(blocks, list):
                            for block in blocks:
                                complexity = block.get("complexity", 0)
                                if complexity >= 6:  # Only flag non-trivial complexity
                                    rank = block.get("rank", "?")
                                    findings.append(ToolFinding(
                                        tool_name="radon",
                                        rule_id="CC",
                                        category="complexity",
                                        severity=_complexity_severity(complexity),
                                        line_start=block.get("lineno", 0),
                                        line_end=block.get("endline", block.get("lineno", 0)),
                                        message=(
                                            f"{block.get('type', 'function')} "
                                            f"'{block.get('name', '?')}' has cyclomatic "
                                            f"complexity of {complexity} (grade {rank})"
                                        ),
                                        evidence=f"complexity={complexity}, rank={rank}",
                                        confidence=0.95,
                                    ))
                except json.JSONDecodeError:
                    logger.warning("Radon CC output was not valid JSON")

            # Maintainability index (mi)
            mi_result = subprocess.run(
                [_PYTHON, "-m", "radon", "mi", "-j", "-s", tmp_file.name],
                capture_output=True, text=True, timeout=30
            )
            if mi_result.stdout.strip():
                try:
                    mi_data = json.loads(mi_result.stdout)
                    for file_path, mi_info in mi_data.items():
                        if isinstance(mi_info, dict):
                            mi_score = mi_info.get("mi", 0)
                            mi_rank = mi_info.get("rank", "?")
                            if mi_score < 20:  # Low maintainability
                                findings.append(ToolFinding(
                                    tool_name="radon",
                                    rule_id="MI",
                                    category="maintainability",
                                    severity="medium" if mi_score >= 10 else "high",
                                    line_start=1,
                                    line_end=len(code.split("\n")),
                                    message=(
                                        f"File maintainability index: {mi_score:.1f} "
                                        f"(grade {mi_rank}) — "
                                        f"{'poor' if mi_score < 10 else 'moderate'} maintainability"
                                    ),
                                    evidence=f"mi={mi_score:.1f}, rank={mi_rank}",
                                    confidence=0.9,
                                ))
                except json.JSONDecodeError:
                    logger.warning("Radon MI output was not valid JSON")

        except FileNotFoundError:
            logger.warning("Radon not installed — skipping complexity analysis")
        except subprocess.TimeoutExpired:
            logger.warning("Radon timed out after 30s")
        except Exception as e:
            logger.warning(f"Radon run failed: {e}")
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass

        return findings


def _complexity_severity(complexity: int) -> str:
    if complexity >= 21:
        return "critical"
    elif complexity >= 11:
        return "high"
    elif complexity >= 6:
        return "medium"
    return "low"


# ── AST Structural Parser (LEDGER case file) ──────────────────────────

class ASTParser:
    """
    Parses Python code structure using the ast module.
    Produces a StructuralIndex that all agents reference.
    """

    @staticmethod
    def parse(code: str, language: str = "python") -> StructuralIndex:
        """Parse code structure into an indexed case file."""
        index = StructuralIndex()

        if not code.strip():
            return index

        lines = code.split("\n")
        index.total_lines = len(lines)

        if language.lower() not in ("python", "py"):
            # Non-Python: basic line-based indexing
            index.functions = _regex_function_scan(code, lines)
            index.total_functions = len(index.functions)
            return index

        try:
            tree = ast.parse(code)
        except SyntaxError:
            logger.debug("AST parse failed for structural indexing")
            return index

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = {
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                    "args": [a.arg for a in node.args.args],
                    "decorators": [
                        _get_decorator_name(d) for d in node.decorator_list
                    ],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }
                index.functions.append(func_info)

                # Scan for nested functions
                for child in ast.walk(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                            and child is not node:
                        index.functions.append({
                            "name": f"{node.name}.{child.name}",
                            "line_start": child.lineno,
                            "line_end": getattr(child, "end_lineno", child.lineno),
                            "args": [a.arg for a in child.args.args],
                            "decorators": [],
                            "is_async": isinstance(child, ast.AsyncFunctionDef),
                            "nested_in": node.name,
                        })

            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append({
                            "name": item.name,
                            "line_start": item.lineno,
                            "line_end": getattr(item, "end_lineno", item.lineno),
                        })
                class_info = {
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                    "bases": [_get_base_name(b) for b in node.bases],
                    "methods": methods,
                    "method_count": len(methods),
                }
                index.classes.append(class_info)

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        index.imports.append({
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "type": "import",
                        })
                else:
                    for alias in node.names:
                        index.imports.append({
                            "module": node.module or "",
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "type": "from_import",
                        })

        index.total_functions = len(index.functions)
        index.total_classes = len(index.classes)
        return index

    @staticmethod
    def format_index(index: StructuralIndex) -> str:
        """Format structural index as readable text for agent prompts."""
        parts = []
        parts.append(
            f"Code structure: {index.total_lines} lines, "
            f"{index.total_functions} functions, {index.total_classes} classes"
        )

        if index.imports:
            import_names = [
                imp.get("module", imp.get("name", "?"))
                for imp in index.imports[:15]
            ]
            parts.append(f"Imports: {', '.join(import_names)}")

        if index.functions:
            func_lines = []
            for f in index.functions[:20]:
                async_tag = "async " if f.get("is_async") else ""
                args = ", ".join(f.get("args", [])[:5])
                if len(f.get("args", [])) > 5:
                    args += ", ..."
                func_lines.append(
                    f"  {async_tag}{f['name']}({args}) "
                    f"[lines {f['line_start']}-{f['line_end']}]"
                )
            parts.append("Functions:\n" + "\n".join(func_lines))

        if index.classes:
            cls_lines = []
            for c in index.classes[:10]:
                bases = ", ".join(c.get("bases", []))
                base_str = f"({bases})" if bases else ""
                method_names = [m["name"] for m in c.get("methods", [])[:8]]
                cls_lines.append(
                    f"  class {c['name']}{base_str} "
                    f"[lines {c['line_start']}-{c['line_end']}, "
                    f"{c['method_count']} methods]"
                )
                if method_names:
                    cls_lines.append(f"    methods: {', '.join(method_names)}")
            parts.append("Classes:\n" + "\n".join(cls_lines))

        return "\n\n".join(parts)


def _get_decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_decorator_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Call):
        return _get_decorator_name(node.func)
    return "?"


def _get_base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_base_name(node.value)}.{node.attr}"
    return "?"


def _regex_function_scan(code: str, lines: list) -> list:
    """Basic regex-based function scan for non-Python languages."""
    import re
    functions = []
    patterns = [
        # JavaScript/TypeScript
        re.compile(r'(?:async\s+)?function\s+(\w+)'),
        re.compile(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>'),
        # Java/C#/C++
        re.compile(r'(?:public|private|protected|static|\s)+\s+\w+\s+(\w+)\s*\('),
        # Go
        re.compile(r'func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\('),
        # Ruby
        re.compile(r'def\s+(\w+)'),
    ]
    for i, line in enumerate(lines, 1):
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                functions.append({
                    "name": match.group(1),
                    "line_start": i,
                    "line_end": i,
                    "args": [],
                    "decorators": [],
                    "is_async": "async" in line,
                })
                break
    return functions


# ── Validation Detector (AXIOM defense evidence) ──────────────────────

class ValidationDetector:
    """
    Detects input validation and sanitization patterns in code.
    Provides AXIOM with concrete evidence that certain areas are protected.
    """

    # Patterns that indicate input validation/sanitization
    VALIDATION_PATTERNS: Dict[str, Dict[str, Any]] = {
        "parameterized_query": {
            "patterns": [
                r"\?.*execute",
                r"%s.*execute",
                r"execute\(.*,\s*\(",
                r"execute\(.*,\s*\[",
                r"execute\(.*,\s*\{",
                r"\.text\(.*\)",
            ],
            "description": "Parameterized SQL query (prevents SQL injection)",
            "protects": ["sql_injection"],
        },
        "input_validation": {
            "patterns": [
                r"isinstance\(",
                r"validate\(",
                r"is_valid\(",
                r"check_type\(",
                r"type_check\(",
                r"assert\s+isinstance",
                r"if\s+not\s+isinstance",
            ],
            "description": "Input type validation check",
            "protects": ["type_confusion", "injection"],
        },
        "sanitization": {
            "patterns": [
                r"escape\(",
                r"sanitize\(",
                r"clean\(",
                r"strip_tags\(",
                r"html\.escape",
                r"bleach\.clean",
                r"markupsafe",
                r"re\.sub\(.*['\"]",
            ],
            "description": "Input sanitization/escaping",
            "protects": ["xss", "injection"],
        },
        "allowlist": {
            "patterns": [
                r"if\s+\w+\s+in\s+\[",
                r"if\s+\w+\s+in\s+\{",
                r"if\s+\w+\s+in\s+\(",
                r"choices\s*=\s*\[",
                r"enum\s*=",
                r"Literal\[",
            ],
            "description": "Allowlist/whitelist validation",
            "protects": ["injection", "unexpected_input"],
        },
        "auth_check": {
            "patterns": [
                r"@login_required",
                r"@requires_auth",
                r"authenticate\(",
                r"verify_token\(",
                r"check_permission\(",
                r"is_authenticated",
                r"@protected",
            ],
            "description": "Authentication/authorization check",
            "protects": ["unauthorized_access"],
        },
        "rate_limiting": {
            "patterns": [
                r"@rate_limit",
                r"throttle\(",
                r"rate_limit",
                r"max_requests",
                r"@limiter",
            ],
            "description": "Rate limiting protection",
            "protects": ["dos", "brute_force"],
        },
    }

    @staticmethod
    def detect(code: str) -> List[ValidationPattern]:
        """Scan code for validation/sanitization patterns."""
        import re
        patterns_found = []
        lines = code.split("\n")

        for pattern_type, config in ValidationDetector.VALIDATION_PATTERNS.items():
            for regex_str in config["patterns"]:
                try:
                    regex = re.compile(regex_str, re.IGNORECASE)
                    for i, line in enumerate(lines, 1):
                        if regex.search(line):
                            # Find the extent of this pattern (multi-line aware)
                            end_line = i
                            for j in range(i, min(i + 3, len(lines))):
                                if lines[j - 1].strip().endswith(("\\", "{", "[")):
                                    end_line = j
                                else:
                                    break
                            patterns_found.append(ValidationPattern(
                                pattern_type=pattern_type,
                                line_start=i,
                                line_end=end_line,
                                description=config["description"],
                                protects_against=config.get("protects", []),
                            ))
                except re.error:
                    continue

        # Deduplicate: keep one pattern per type per line range
        seen = set()
        deduped = []
        for p in patterns_found:
            key = (p.pattern_type, p.line_start)
            if key not in seen:
                seen.add(key)
                deduped.append(p)

        return deduped

    @staticmethod
    def format_patterns(patterns: List[ValidationPattern]) -> str:
        """Format validation patterns for agent prompt inclusion."""
        if not patterns:
            return "No validation/sanitization patterns detected."

        lines = ["Detected validation/sanitization patterns:"]
        for p in patterns:
            protects = ", ".join(p.protects_against) if p.protects_against else "general"
            lines.append(
                f"  - {p.pattern_type} (lines {p.line_start}-{p.line_end}): "
                f"{p.description} [protects: {protects}]"
            )
        return "\n".join(lines)

    @staticmethod
    def find_defense_for_line(
        target_line: int, patterns: List[ValidationPattern]
    ) -> Optional[ValidationPattern]:
        """
        Check if there's a validation pattern that could protect
        a specific line (i.e., validation occurs before the target).
        """
        for p in patterns:
            # Validation must occur before or at the target line
            if p.line_start <= target_line:
                return p
        return None
