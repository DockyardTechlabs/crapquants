"""
Merge layer — joins complexity and coverage data to produce CRAP scores.

Handles the path normalization problem identified in cargo-crap:
LCOV files can contain absolute paths, workspace-relative paths,
crate-relative paths, or paths with ./ or ../ components.

Strategy: canonical path comparison with suffix fallback.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import structlog

from crapquants.core.complexity import FileMetrics, FunctionMetrics
from crapquants.core.coverage_parser import (
    FileCoverage,
    FunctionCoverage,
    estimate_function_coverage,
)
from crapquants.core.crap import CRAPResult, compute_crap_result

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MergedFunctionResult:
    """Complete merged result for a single function — metrics + coverage + CRAP."""

    metrics: FunctionMetrics
    coverage: FunctionCoverage | None
    crap: CRAPResult


@dataclass(frozen=True)
class MergedFileResult:
    """Complete merged result for a single file."""

    file_path: str
    file_metrics: FileMetrics
    file_coverage: FileCoverage | None
    functions: list[MergedFunctionResult]


def normalize_path(path: str) -> str:
    """
    Normalize a file path for comparison.

    Handles:
        - Absolute vs relative paths
        - ./ and ../ components
        - OS-specific separators
        - Trailing slashes

    Args:
        path: Raw file path string.

    Returns:
        Normalized path string (lowercase on Windows, forward slashes).
    """
    normalized = os.path.normpath(path)
    normalized = normalized.replace("\\", "/")
    # Remove leading ./
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def match_coverage_to_file(
    file_path: str,
    coverage_data: list[FileCoverage],
) -> FileCoverage | None:
    """
    Find the coverage data matching a source file.

    Uses two-level matching strategy (from cargo-crap):
    1. Direct canonical path match
    2. Suffix matching on path components

    Args:
        file_path: Source file path (from complexity analysis).
        coverage_data: List of all parsed coverage records.

    Returns:
        Matching FileCoverage or None.
    """
    norm_target = normalize_path(file_path)

    # Level 1: Direct canonical match
    for cov in coverage_data:
        if normalize_path(cov.file_path) == norm_target:
            return cov

    # Level 2: Suffix matching — compare last N path components
    target_parts = norm_target.split("/")

    best_match: FileCoverage | None = None
    best_match_depth = 0

    for cov in coverage_data:
        cov_parts = normalize_path(cov.file_path).split("/")

        # Count matching suffix components
        match_depth = 0
        for t, c in zip(reversed(target_parts), reversed(cov_parts)):
            if t == c:
                match_depth += 1
            else:
                break

        if match_depth > best_match_depth and match_depth >= 2:
            best_match = cov
            best_match_depth = match_depth

    if best_match:
        logger.debug(
            "coverage_suffix_match",
            source_file=file_path,
            coverage_file=best_match.file_path,
            depth=best_match_depth,
        )

    return best_match


def merge_file(
    file_metrics: FileMetrics,
    coverage_data: list[FileCoverage],
    crap_threshold: float = 30.0,
    missing_policy: str = "pessimistic",
) -> MergedFileResult:
    """
    Merge complexity metrics with coverage data for a single file.

    Args:
        file_metrics: Complexity metrics for the file.
        coverage_data: All parsed coverage records.
        crap_threshold: CRAP score threshold (default 30).
        missing_policy: How to handle functions with no coverage data:
            - "pessimistic": Treat as 0% covered (safe for CI gates)
            - "optimistic": Treat as 100% covered (useful for local dev)
            - "skip": Exclude from results

    Returns:
        MergedFileResult with CRAP scores for each function.
    """
    file_coverage = match_coverage_to_file(file_metrics.file_path, coverage_data)

    merged_functions: list[MergedFunctionResult] = []

    for func in file_metrics.functions:
        func_cov: FunctionCoverage | None = None
        coverage_pct: float

        if file_coverage:
            func_cov = estimate_function_coverage(
                file_coverage,
                func.name,
                func.line_start,
                func.line_end,
            )
            coverage_pct = func_cov.coverage_percent
        else:
            # No coverage data for this file
            if missing_policy == "pessimistic":
                coverage_pct = 0.0
            elif missing_policy == "optimistic":
                coverage_pct = 100.0
            elif missing_policy == "skip":
                continue
            else:
                coverage_pct = 0.0

        crap = compute_crap_result(
            function_name=func.name,
            file_path=func.file_path,
            line_number=func.line_start,
            complexity=func.cyclomatic_complexity,
            coverage=coverage_pct,
            threshold=crap_threshold,
        )

        merged_functions.append(
            MergedFunctionResult(
                metrics=func,
                coverage=func_cov,
                crap=crap,
            )
        )

    logger.info(
        "file_merged",
        file=file_metrics.file_path,
        functions=len(merged_functions),
        coverage_found=file_coverage is not None,
    )

    return MergedFileResult(
        file_path=file_metrics.file_path,
        file_metrics=file_metrics,
        file_coverage=file_coverage,
        functions=merged_functions,
    )


def merge_all(
    file_metrics_list: list[FileMetrics],
    coverage_data: list[FileCoverage],
    crap_threshold: float = 30.0,
    missing_policy: str = "pessimistic",
) -> list[MergedFileResult]:
    """
    Merge all file metrics with coverage data.

    Args:
        file_metrics_list: List of FileMetrics from complexity analysis.
        coverage_data: List of FileCoverage from coverage parsing.
        crap_threshold: CRAP score threshold.
        missing_policy: Policy for missing coverage data.

    Returns:
        List of MergedFileResult, one per file.
    """
    results = []
    for fm in file_metrics_list:
        merged = merge_file(fm, coverage_data, crap_threshold, missing_policy)
        results.append(merged)

    total_functions = sum(len(r.functions) for r in results)
    crappy_count = sum(
        1 for r in results for f in r.functions if f.crap.is_crappy
    )

    logger.info(
        "merge_complete",
        files=len(results),
        total_functions=total_functions,
        crappy_functions=crappy_count,
    )

    return results
