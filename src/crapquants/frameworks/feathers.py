"""
Feathers Framework — Testability risk analysis.

Source: Working Effectively with Legacy Code (Michael Feathers, 2005)

Provides:
    - FRS (Feathers Risk Score): CRAP × monster_multiplier × dependency_depth × responsibility_factor
    - TI (Testability Index): 0-100 inverse of how hard it is to get under test
    - Monster classification (Bulleted vs Snarled)
    - 12 diagnostic tags
    - Dependency-breaking technique recommendations

Attacks the cov(m) side of the CRAP formula.
"""

from __future__ import annotations

from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.tags import (
    DiagnosticTag,
    Framework,
    FunctionDiagnostics,
    Recommendation,
    Severity,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MONSTER_CC_THRESHOLD = 10
_BULLETED_MAX_NESTING = 3
_BULLETED_MIN_LINES = 50
_SNARLED_MIN_NESTING = 4
_EDIT_PRAY_CC_THRESHOLD = 5
_HIDDEN_CLASS_RATIO = 2.0  # private > 2× public
_DILEMMA_DEP_DEPTH = 4
_REFACTOR_MANDATORY_CC = 31


# ---------------------------------------------------------------------------
# Tag factory helpers
# ---------------------------------------------------------------------------

def _tag(tag_id: str, severity: Severity, desc: str,
         recs: tuple[Recommendation, ...] = ()) -> DiagnosticTag:
    return DiagnosticTag(
        tag_id=tag_id,
        framework=Framework.FEATHERS,
        severity=severity,
        description=desc,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Monster classification
# ---------------------------------------------------------------------------

def classify_monster(cc: int, max_nesting: int, line_count: int) -> str | None:
    """
    Classify a function as a Feathers Monster type.

    Returns:
        "SNARLED" | "BULLETED" | "COMPLEX_BUT_COMPACT" | None
    """
    if cc <= _MONSTER_CC_THRESHOLD:
        return None
    if max_nesting >= _SNARLED_MIN_NESTING:
        return "SNARLED"
    if line_count >= _BULLETED_MIN_LINES:
        return "BULLETED"
    return "COMPLEX_BUT_COMPACT"


def monster_multiplier(monster_type: str | None) -> float:
    """Risk multiplier based on monster type."""
    return {"SNARLED": 1.5, "BULLETED": 1.2, "COMPLEX_BUT_COMPACT": 1.0}.get(
        monster_type, 1.0
    )


# ---------------------------------------------------------------------------
# Composite scores
# ---------------------------------------------------------------------------

def compute_frs(
    crap: float,
    monster_type: str | None,
    dependency_depth: int = 0,
    responsibility_count: int = 1,
) -> float:
    """
    Feathers Risk Score — CRAP amplified by testability factors.

    FRS = CRAP × monster_mult × (1 + dep_depth/10) × responsibility_factor
    """
    m_mult = monster_multiplier(monster_type)
    dep_factor = 1.0 + (dependency_depth / 10.0)
    resp_factor = 1.3 if responsibility_count > 1 else 1.0
    return round(crap * m_mult * dep_factor * resp_factor, 2)


def compute_testability_index(
    dependency_depth: int = 0,
    has_sensing_problem: bool = False,
    has_separation_problem: bool = False,
) -> float:
    """
    Testability Index — inverse of how hard to get under test.

    TI = 100 - (dep_depth × 10) - (sensing × 15) - (separation × 20)
    Clamped to [0, 100].
    """
    ti = 100.0
    ti -= dependency_depth * 10
    ti -= 15 if has_sensing_problem else 0
    ti -= 20 if has_separation_problem else 0
    return max(0.0, min(100.0, ti))


# ---------------------------------------------------------------------------
# Diagnostic analysis
# ---------------------------------------------------------------------------

def analyze(result: MergedFunctionResult) -> list[DiagnosticTag]:
    """
    Run Feathers diagnostic analysis on a merged function result.

    Args:
        result: Merged function data (metrics + coverage + CRAP).

    Returns:
        List of applicable Feathers diagnostic tags.
    """
    tags: list[DiagnosticTag] = []
    m = result.metrics
    c = result.crap

    cc = m.cyclomatic_complexity
    cov = c.coverage
    nesting = m.max_nesting_depth
    lines = m.line_count

    # --- Monster classification ---
    monster = classify_monster(cc, nesting, lines)

    if monster == "SNARLED":
        tags.append(_tag(
            "MONSTER_SNARLED", Severity.HIGH,
            f"Snarled monster method: CC={cc}, nesting={nesting}. "
            f"Deep nesting interleaves state, making decomposition risky.",
            (
                Recommendation("Introduce Sensing Variable", "Verify branch execution before extracting", 1),
                Recommendation("Replace Method with Method Object", "Convert to class to untangle state", 2),
                Recommendation("Decompose Conditional", "Simplify nested branches", 3),
            ),
        ))
    elif monster == "BULLETED":
        tags.append(_tag(
            "MONSTER_BULLETED", Severity.WARNING,
            f"Bulleted monster method: CC={cc}, lines={lines}. "
            f"Low nesting but long sequential sections.",
            (
                Recommendation("Extract Method", "One extraction per code section/bullet", 1),
            ),
        ))

    # --- Edit and Pray ---
    if cov == 0.0 and cc > _EDIT_PRAY_CC_THRESHOLD:
        tags.append(_tag(
            "EDIT_AND_PRAY", Severity.HIGH,
            f"No test coverage (0%) with CC={cc}. "
            f"Any change is Edit and Pray — no safety net.",
            (
                Recommendation("Write Characterization Tests", "Document actual behavior before changing", 1),
            ),
        ))

    # --- Characterization needed ---
    if cov == 0.0 and c.crap_score > 30:
        tags.append(_tag(
            "CHARACTERIZATION_NEEDED", Severity.HIGH,
            f"CRAP={c.crap_score:.1f} with 0% coverage. "
            f"Write characterization tests documenting current behavior first.",
            (
                Recommendation("Write Characterization Tests", "Use Feathers' algorithm: assert wrong, let failure teach you", 1),
            ),
        ))

    # --- Legacy Code Dilemma ---
    if c.crap_score > 30 and m.parameter_count >= _DILEMMA_DEP_DEPTH:
        tags.append(_tag(
            "LEGACY_DILEMMA", Severity.CRITICAL,
            f"CRAP={c.crap_score:.1f} with {m.parameter_count} parameters. "
            f"High complexity + high dependency depth = Legacy Code Dilemma. "
            f"Must break dependencies before testing is possible.",
            (
                Recommendation("Extract Interface / Protocol", "Create Protocol for dependency injection", 1),
                Recommendation("Parameterize Constructor", "Break hard dependencies", 2),
            ),
        ))

    # --- Refactor mandatory (CC >= 31) ---
    if cc >= _REFACTOR_MANDATORY_CC:
        tags.append(_tag(
            "REFACTOR_MANDATORY", Severity.CRITICAL,
            f"CC={cc} exceeds absolute threshold of 31. "
            f"No amount of testing can make this maintainable — must reduce complexity.",
            (
                Recommendation("Replace Method with Method Object", "Distribute CC across class methods", 1),
                Recommendation("Decompose Conditional", "Break conditional chains", 2),
                Recommendation("Replace Conditional with Polymorphism", "Eliminate branching entirely", 3),
            ),
        ))

    # --- Sensing problem (returns None but has side effects) ---
    # Approximation: functions with no return annotation or returning None
    # and high parameter count (likely modifying state)
    if m.parameter_count >= 3 and cc > 5 and cov < 50:
        tags.append(_tag(
            "SENSING_PROBLEM", Severity.WARNING,
            f"High complexity (CC={cc}) with {m.parameter_count} params and low coverage ({cov:.0f}%). "
            f"Likely has side effects that are hard to sense in tests.",
            (
                Recommendation("Separate Query from Modifier", "Split read from write", 1),
                Recommendation("Extract Method", "Isolate side-effecting code", 2),
            ),
        ))

    return tags
