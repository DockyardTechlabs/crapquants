"""
Ford Framework — Architectural fitness functions.

Source: Building Evolutionary Architectures, 2nd Ed (Neal Ford et al., 2023)

Provides:
    - Fitness function registry
    - CRAP threshold fitness function
    - CRAP regression fitness function
    - Cycle detection (import graph analysis) — Phase 6/7
    - Layering rule enforcement — Phase 6/7

CRAPQuants itself IS an architectural fitness function for
the "maintainability" dimension.
"""

from __future__ import annotations

from dataclasses import dataclass

from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.tags import (
    DiagnosticTag,
    Framework,
    Recommendation,
    Severity,
)


# ---------------------------------------------------------------------------
# Fitness function definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FitnessFunction:
    """Ford-style fitness function registration."""

    name: str
    dimension: str  # e.g., "maintainability", "modularity", "security"
    scope: str  # "atomic" | "holistic"
    threshold: float
    description: str


# Built-in fitness functions
BUILTIN_FITNESS_FUNCTIONS = (
    FitnessFunction(
        name="crap_threshold",
        dimension="maintainability",
        scope="atomic",
        threshold=30.0,
        description="No function should exceed CRAP score of 30",
    ),
    FitnessFunction(
        name="crap_regression",
        dimension="maintainability",
        scope="holistic",
        threshold=0.0,
        description="Aggregate CRAP must not increase between baseline and current",
    ),
    FitnessFunction(
        name="cognitive_complexity_threshold",
        dimension="understandability",
        scope="atomic",
        threshold=15.0,
        description="No function should exceed Cognitive Complexity of 15",
    ),
    FitnessFunction(
        name="abc_threshold",
        dimension="size",
        scope="atomic",
        threshold=30.0,
        description="No function should exceed ABC scalar of 30",
    ),
)


# ---------------------------------------------------------------------------
# Tag factory
# ---------------------------------------------------------------------------

def _tag(tag_id: str, severity: Severity, desc: str,
         recs: tuple[Recommendation, ...] = ()) -> DiagnosticTag:
    return DiagnosticTag(
        tag_id=tag_id,
        framework=Framework.FORD,
        severity=severity,
        description=desc,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Fitness function evaluation
# ---------------------------------------------------------------------------

def evaluate_fitness(
    result: MergedFunctionResult,
    crap_threshold: float = 30.0,
    cogc_threshold: float = 15.0,
    abc_threshold: float = 30.0,
) -> list[DiagnosticTag]:
    """
    Evaluate architectural fitness functions against a function.

    Args:
        result: Merged function data.
        crap_threshold: CRAP score threshold.
        cogc_threshold: Cognitive Complexity threshold.
        abc_threshold: ABC scalar threshold.

    Returns:
        List of fitness function violation tags.
    """
    tags: list[DiagnosticTag] = []
    m = result.metrics
    c = result.crap

    # CRAP threshold fitness function
    if c.crap_score > crap_threshold:
        tags.append(_tag(
            "FITNESS_CRAP_EXCEEDED", Severity.HIGH,
            f"CRAP fitness function FAILED: {c.crap_score:.1f} > {crap_threshold}. "
            f"Function exceeds maintainability threshold.",
            (
                Recommendation("Reduce complexity or increase coverage",
                               f"Need coverage >= {c.min_coverage_needed:.0f}% at current CC, "
                               f"or reduce CC below {int(crap_threshold ** 0.5)}", 1),
            ),
        ))

    # Cognitive Complexity threshold
    if m.cognitive_complexity > cogc_threshold:
        tags.append(_tag(
            "FITNESS_COGC_EXCEEDED", Severity.WARNING,
            f"Cognitive Complexity fitness function FAILED: "
            f"{m.cognitive_complexity} > {cogc_threshold}. "
            f"Function exceeds understandability threshold.",
            (
                Recommendation("Decompose Conditional", "Reduce nesting and branching", 1),
                Recommendation("Extract Method", "Break into smaller, named pieces", 2),
            ),
        ))

    # ABC threshold
    if m.abc_scalar > abc_threshold:
        tags.append(_tag(
            "FITNESS_ABC_EXCEEDED", Severity.WARNING,
            f"ABC fitness function FAILED: "
            f"{m.abc_scalar:.1f} > {abc_threshold}. "
            f"Function does too much (A={m.abc_assignments}, B={m.abc_branches}, C={m.abc_conditions}).",
            (
                Recommendation("Extract Method", "Reduce assignments and calls per function", 1),
            ),
        ))

    return tags


def analyze(result: MergedFunctionResult) -> list[DiagnosticTag]:
    """Run Ford fitness function evaluation."""
    return evaluate_fitness(result)
