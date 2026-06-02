"""
Complexity computation module.

Wraps radon for Cyclomatic Complexity and provides integration
with custom AST visitors for Cognitive Complexity and ABC metric.

Sources:
    - CC: Thomas J. McCabe (1976), via radon (MIT)
    - CogC: G. Ann Campbell / SonarSource (2023)
    - ABC: Assignments, Branches, Conditions metric
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import structlog
from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze

from crapquants.core.ast_visitors import (
    ABCResult,
    CognitiveComplexityResult,
    compute_abc,
    compute_cognitive_complexity,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class FunctionMetrics:
    """Complete complexity metrics for a single function."""

    name: str
    file_path: str
    line_start: int
    line_end: int

    # McCabe Cyclomatic Complexity (via radon)
    cyclomatic_complexity: int

    # SonarSource Cognitive Complexity
    cognitive_complexity: int

    # ABC Metric
    abc_assignments: int
    abc_branches: int
    abc_conditions: int
    abc_scalar: float

    # Raw metrics
    line_count: int
    max_nesting_depth: int
    parameter_count: int


@dataclass(frozen=True)
class FileMetrics:
    """Complexity metrics for an entire file."""

    file_path: str
    functions: list[FunctionMetrics]

    # Halstead metrics (file-level via radon)
    halstead_volume: float
    halstead_difficulty: float
    halstead_effort: float

    # Maintainability Index (file-level via radon)
    maintainability_index: float

    # Raw file metrics
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int


def analyze_file(file_path: str | Path) -> FileMetrics:
    """
    Analyze a Python file for all complexity metrics.

    Reads the file, computes CC (radon), CogC, ABC (custom AST),
    Halstead, MI, and raw metrics.

    Args:
        file_path: Path to the Python source file.

    Returns:
        FileMetrics with all computed metrics.

    Raises:
        FileNotFoundError: If file doesn't exist.
        SyntaxError: If file contains invalid Python.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    source = file_path.read_text(encoding="utf-8")

    # Radon CC analysis (per-function)
    cc_results = cc_visit(source)

    # Radon raw metrics (file-level)
    raw = analyze(source)

    # Radon Halstead metrics (file-level)
    try:
        halstead = h_visit(source)
        h_total = halstead.total
        h_volume = h_total.volume if h_total.volume else 0.0
        h_difficulty = h_total.difficulty if h_total.difficulty else 0.0
        h_effort = h_total.effort if h_total.effort else 0.0
    except Exception:
        logger.warning("halstead_failed", file=str(file_path))
        h_volume = 0.0
        h_difficulty = 0.0
        h_effort = 0.0

    # Radon Maintainability Index (file-level)
    try:
        mi = mi_visit(source, multi=True)
    except Exception:
        logger.warning("mi_failed", file=str(file_path))
        mi = 0.0

    # Custom AST analysis (per-function CogC, ABC, nesting, params)
    cogc_results = compute_cognitive_complexity(source)
    abc_results = compute_abc(source)

    # Build per-function FunctionMetrics
    functions: list[FunctionMetrics] = []

    for cc_func in cc_results:
        func_name = cc_func.name
        line_start = cc_func.lineno
        line_end = cc_func.endline if hasattr(cc_func, "endline") and cc_func.endline else line_start

        # Match CogC result by function name + line
        cogc = _find_matching(cogc_results, func_name, line_start)
        abc = _find_matching_abc(abc_results, func_name, line_start)

        fm = FunctionMetrics(
            name=func_name,
            file_path=str(file_path),
            line_start=line_start,
            line_end=line_end,
            cyclomatic_complexity=cc_func.complexity,
            cognitive_complexity=cogc.score if cogc else 0,
            abc_assignments=abc.assignments if abc else 0,
            abc_branches=abc.branches if abc else 0,
            abc_conditions=abc.conditions if abc else 0,
            abc_scalar=abc.scalar if abc else 0.0,
            line_count=max(1, line_end - line_start + 1),
            max_nesting_depth=cogc.max_nesting if cogc else 0,
            parameter_count=abc.parameter_count if abc else 0,
        )
        functions.append(fm)

    file_metrics = FileMetrics(
        file_path=str(file_path),
        functions=functions,
        halstead_volume=round(h_volume, 2),
        halstead_difficulty=round(h_difficulty, 2),
        halstead_effort=round(h_effort, 2),
        maintainability_index=round(mi, 2) if isinstance(mi, (int, float)) else 0.0,
        total_lines=raw.loc,
        code_lines=raw.sloc,
        comment_lines=raw.comments,
        blank_lines=raw.blank,
    )

    logger.info(
        "file_analyzed",
        file=str(file_path),
        functions=len(functions),
        total_lines=raw.loc,
    )

    return file_metrics


def _find_matching(
    results: list[CognitiveComplexityResult],
    name: str,
    line: int,
) -> CognitiveComplexityResult | None:
    """Find CogC result matching function name and line number."""
    for r in results:
        if r.name == name and r.line_start == line:
            return r
    # Fallback: match by name only (line numbers may differ slightly)
    for r in results:
        if r.name == name:
            return r
    return None


def _find_matching_abc(
    results: list[ABCResult],
    name: str,
    line: int,
) -> ABCResult | None:
    """Find ABC result matching function name and line number."""
    for r in results:
        if r.name == name and r.line_start == line:
            return r
    for r in results:
        if r.name == name:
            return r
    return None
