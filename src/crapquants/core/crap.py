"""
CRAP (Change Risk Anti-Patterns) formula implementation.

Formula: CRAP(m) = comp(m)² × (1 − cov(m)/100)³ + comp(m)

Source: Alberto Savoia & Bob Evans, 2007 (Crap4J)
Threshold: CRAP > 30 = CRAPpy

Also includes CRAPload calculation — minimum work units to get below threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CRAPResult:
    """Result of CRAP score computation for a single function."""

    function_name: str
    file_path: str
    line_number: int
    complexity: int
    coverage: float  # 0.0 to 100.0
    crap_score: float
    crapload: int
    is_crappy: bool
    min_coverage_needed: float  # Minimum coverage to get below threshold at current CC
    complexity_threshold_exceeded: bool  # CC >= 31 means refactor mandatory


def calculate_crap(complexity: int, coverage: float) -> float:
    """
    Calculate the CRAP score for a function.

    Args:
        complexity: Cyclomatic complexity of the function.
        coverage: Code coverage percentage (0.0 to 100.0).

    Returns:
        CRAP score as a float.

    Raises:
        ValueError: If coverage is outside [0.0, 100.0] or complexity is negative.
    """
    if complexity < 0:
        raise ValueError(f"Complexity must be non-negative, got {complexity}")
    if not 0.0 <= coverage <= 100.0:
        raise ValueError(f"Coverage must be between 0.0 and 100.0, got {coverage}")

    cov_factor = 1.0 - (coverage / 100.0)
    crap = (complexity ** 2) * (cov_factor ** 3) + complexity

    return round(crap, 2)


def calculate_crapload(
    crap_score: float,
    complexity: int,
    coverage: float,
    threshold: float = 30.0,
) -> int:
    """
    Calculate CRAPload — minimum work units to get below CRAP threshold.

    From Crap4J FAQ:
    - For every point of uncovered complexity: +1 test needed.
    - For every unit of complexity over threshold: +1 extract-method refactoring.

    Args:
        crap_score: Current CRAP score.
        complexity: Cyclomatic complexity.
        coverage: Code coverage percentage (0.0 to 100.0).
        threshold: CRAP threshold (default 30).

    Returns:
        Estimated minimum work units (tests + refactorings).
    """
    if crap_score <= threshold:
        return 0

    crapload = 0

    # Tests needed to cover uncovered paths
    uncovered_paths = int(complexity * (1.0 - coverage / 100.0))
    crapload += uncovered_paths

    # Refactorings needed if complexity exceeds what testing alone can fix
    if complexity >= 31:
        # Number of extract-method refactorings (halving complexity each time)
        refactorings_needed = max(0, int(math.log2(complexity / 15.0)))
        crapload += refactorings_needed

    return crapload


def min_coverage_for_threshold(complexity: int, threshold: float = 30.0) -> float:
    """
    Calculate minimum coverage needed to stay below CRAP threshold
    at a given complexity level.

    From Crap4J complexity-coverage threshold table:
        CC 0-5:   0%
        CC 6-10:  42%
        CC 11-15: 57%
        CC 16-20: 71%
        CC 21-25: 80%
        CC 26-30: 100%
        CC 31+:   Refactor required (returns 100.0 but flags separately)

    Args:
        complexity: Cyclomatic complexity.
        threshold: CRAP threshold (default 30).

    Returns:
        Minimum coverage percentage (0.0 to 100.0).
    """
    if complexity <= 0:
        return 0.0
    if complexity >= 31:
        return 100.0

    # Solve for coverage: threshold = CC² × (1 - cov/100)³ + CC
    # (1 - cov/100)³ = (threshold - CC) / CC²
    # (1 - cov/100) = ((threshold - CC) / CC²) ^ (1/3)
    # cov = 100 × (1 - ((threshold - CC) / CC²) ^ (1/3))
    numerator = threshold - complexity
    denominator = complexity ** 2

    if numerator <= 0:
        return 100.0

    ratio = numerator / denominator
    if ratio >= 1.0:
        return 0.0

    cov_fraction = 1.0 - (ratio ** (1.0 / 3.0))
    return round(max(0.0, min(100.0, cov_fraction * 100.0)), 1)


def compute_crap_result(
    function_name: str,
    file_path: str,
    line_number: int,
    complexity: int,
    coverage: float,
    threshold: float = 30.0,
) -> CRAPResult:
    """
    Compute complete CRAP analysis for a single function.

    Args:
        function_name: Name of the function being analyzed.
        file_path: Path to the source file.
        line_number: Line number where the function starts.
        complexity: Cyclomatic complexity.
        coverage: Code coverage percentage (0.0 to 100.0).
        threshold: CRAP threshold (default 30).

    Returns:
        CRAPResult with all computed metrics.
    """
    crap_score = calculate_crap(complexity, coverage)
    is_crappy = crap_score > threshold
    crapload = calculate_crapload(crap_score, complexity, coverage, threshold)
    min_cov = min_coverage_for_threshold(complexity, threshold)
    cc_exceeded = complexity >= 31

    logger.debug(
        "crap_computed",
        function=function_name,
        file=file_path,
        line=line_number,
        cc=complexity,
        coverage=coverage,
        crap=crap_score,
        is_crappy=is_crappy,
        crapload=crapload,
    )

    return CRAPResult(
        function_name=function_name,
        file_path=file_path,
        line_number=line_number,
        complexity=complexity,
        coverage=coverage,
        crap_score=crap_score,
        crapload=crapload,
        is_crappy=is_crappy,
        min_coverage_needed=min_cov,
        complexity_threshold_exceeded=cc_exceeded,
    )
