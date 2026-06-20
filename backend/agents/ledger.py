"""
CodeTribunal - LEDGER Agent (The Clerk)
Uses the AST module for real structural parsing — not LLM guessing.
Produces an indexed case file that all agents reference.
"""

import logging
from .base import (
    BaseAgent, AgentRole, ProceedingEntry,
    TokenUsageLog, truncate_code, build_transcript, TrialPhase,
)
from .tools import ASTParser
from ..config import settings
from ..system_prompts import LEDGER_SYSTEM_PROMPT

logger = logging.getLogger("codetribunal.agents")


class LedgerAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.LEDGER, settings.LEDGER_MODEL, LEDGER_SYSTEM_PROMPT)

    async def process(self, context: dict) -> ProceedingEntry:
        code = context.get("code_content", "")
        language = context.get("language", "unknown")
        lines_of_code = len(code.split("\n")) if code else 0
        file_size = len(code.encode("utf-8")) if code else 0

        # Real structural parsing via AST (Python) or regex (other languages)
        structural_index = ASTParser.parse(code, language)
        structural_summary = ASTParser.format_index(structural_index)

        # Store parsed structure in context for all agents to use
        context["structural_index"] = structural_index
        context["parsed_info"] = {
            "lines_of_code": lines_of_code,
            "file_size": file_size,
            "language": language,
            "functions": structural_index.functions,
            "classes": structural_index.classes,
            "imports": structural_index.imports,
        }

        # LLM only handles non-Python or edge cases where AST failed
        # For Python, the AST output IS the case file — no LLM hallucination
        if language.lower() in ("python", "py") and structural_index.total_functions > 0:
            message = (
                f"Case filed. Parsed {lines_of_code} lines of {language} code "
                f"({file_size} bytes). "
                f"Found {structural_index.total_functions} functions and "
                f"{structural_index.total_classes} classes via AST analysis.\n\n"
                f"{structural_summary}"
            )
            return self._entry(
                "Case Filed", message, 0, 0.95,
                phase=TrialPhase.INVESTIGATION,
                speaker=self.name,
            )

        # Fallback: use LLM for non-Python code structure
        safe_code = truncate_code(code, max_lines=100, max_chars=4000)
        prompt = (
            f"Parse and document the following {language} code.\n"
            f"Lines: {lines_of_code}, Size: {file_size} bytes.\n\n"
            f"```\n{safe_code}\n```\n\n"
            f"Automated scan found:\n{structural_summary}\n\n"
            f"Provide a brief structural summary: functions, classes, imports, "
            f"and notable patterns."
        )

        content, usage = await self._call_llm(prompt, temperature=0.3, max_tokens=600)
        context.setdefault("token_usage", TokenUsageLog()).record(usage)

        return self._entry(
            "Case Filed", content, 0, 0.9,
            phase=TrialPhase.INVESTIGATION,
            speaker=self.name,
        )
