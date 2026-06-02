"""
AI explainer — generates human-readable explanations of CRAP findings.

Takes a function's metrics, diagnostic tags, and refactoring recommendations,
builds a structured prompt, and calls the configured LLM provider for a
contextualized explanation.

This module is OPTIONAL. CRAPQuants works fully without it.
AI explains WHY a function is problematic and HOW to fix it,
using the actual code context — not generic advice.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.tags import DiagnosticTag
from crapquants.ai_explain.provider import ProviderConfig, call_llm

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are CRAPQuants AI Explainer — a code quality advisor that helps developers 
understand and fix problematic functions.

You receive:
1. A Python function's metrics (CRAP score, complexity, coverage, etc.)
2. Diagnostic tags from six software engineering books
3. Recommended refactoring actions

Your job:
- Explain in plain English WHY this function is problematic (using the metrics)
- Explain WHAT each diagnostic tag means in the context of THIS specific function
- Explain HOW to apply the recommended refactoring, with a concrete example if possible
- Keep explanations concise (under 300 words)
- Be actionable — the developer should know exactly what to do after reading

Format your response as:
## Why This Matters
<1-2 sentences on the risk>

## What The Tags Mean
<bullet list explaining each tag in context>

## What To Do
<numbered steps, most impactful first>

Do NOT repeat the raw metrics — the developer can already see those in the report.
Focus on insight and action."""


def build_prompt(
    result: MergedFunctionResult,
    tags: list[DiagnosticTag],
    source_snippet: str | None = None,
) -> str:
    """
    Build a context-rich prompt from function data + tags.

    Args:
        result: Merged function result with all metrics.
        tags: Diagnostic tags for this function.
        source_snippet: First 50 lines of the function source (optional).

    Returns:
        Formatted prompt string for the LLM.
    """
    m = result.metrics
    c = result.crap

    prompt_parts = [
        f"Function: {m.name} in {m.file_path} (lines {m.line_start}-{m.line_end})",
        f"CRAP Score: {c.crap_score:.1f} (threshold: 30)",
        f"Cyclomatic Complexity: {m.cyclomatic_complexity}",
        f"Cognitive Complexity: {m.cognitive_complexity}",
        f"Coverage: {c.coverage:.0f}%",
        f"ABC: A={m.abc_assignments}, B={m.abc_branches}, C={m.abc_conditions} (scalar={m.abc_scalar:.1f})",
        f"Parameters: {m.parameter_count}",
        f"Nesting Depth: {m.max_nesting_depth}",
        f"Lines: {m.line_count}",
        "",
        "Diagnostic Tags:",
    ]

    for tag in tags:
        rec_text = ""
        if tag.recommendations:
            recs = [f"{r.action} ({r.rationale})" for r in tag.recommendations[:2]]
            rec_text = f" → Recommended: {'; '.join(recs)}"
        prompt_parts.append(
            f"  [{tag.framework.value}] {tag.tag_id} ({tag.severity.value}): "
            f"{tag.description}{rec_text}"
        )

    if source_snippet:
        prompt_parts.extend([
            "",
            "Source code (first 50 lines):",
            "```python",
            source_snippet,
            "```",
        ])

    prompt_parts.extend([
        "",
        "Please explain this function's problems and how to fix them.",
    ])

    return "\n".join(prompt_parts)


def explain_function(
    result: MergedFunctionResult,
    tags: list[DiagnosticTag],
    config: ProviderConfig,
    source_snippet: str | None = None,
) -> str | None:
    """
    Generate an AI explanation for a problematic function.

    Args:
        result: Merged function result.
        tags: Diagnostic tags for this function.
        config: AI provider configuration.
        source_snippet: Optional source code snippet.

    Returns:
        AI-generated explanation string, or None on failure.
    """
    if not tags:
        return None

    prompt = build_prompt(result, tags, source_snippet)

    logger.debug(
        "ai_explain_request",
        function=result.metrics.name,
        provider=config.provider.value,
        tags=len(tags),
    )

    response = call_llm(config, SYSTEM_PROMPT, prompt)

    if response:
        logger.info(
            "ai_explain_success",
            function=result.metrics.name,
            chars=len(response),
        )
    else:
        logger.warning(
            "ai_explain_failed",
            function=result.metrics.name,
        )

    return response


def read_source_snippet(
    file_path: str,
    line_start: int,
    line_end: int,
    max_lines: int = 50,
) -> str | None:
    """
    Read a function's source code for inclusion in AI prompt.

    Args:
        file_path: Path to source file.
        line_start: First line of function.
        line_end: Last line of function.
        max_lines: Maximum lines to include.

    Returns:
        Source code string, or None if file can't be read.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None

        lines = path.read_text(encoding="utf-8").splitlines()
        start = max(0, line_start - 1)
        end = min(len(lines), line_end)
        snippet_lines = lines[start:end]

        if len(snippet_lines) > max_lines:
            snippet_lines = snippet_lines[:max_lines]
            snippet_lines.append("# ... (truncated)")

        return "\n".join(snippet_lines)
    except Exception:
        return None
