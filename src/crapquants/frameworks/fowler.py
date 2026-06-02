"""
Fowler Framework — Refactoring recommendation engine.

Source: Refactoring: Improving the Design of Existing Code (Martin Fowler, Kent Beck)

Provides:
    - 22 code smell detections (subset automatable via static analysis)
    - Tag → Refactoring mapping from all frameworks
    - Priority algorithm (CC reducers → coverage enablers → interface simplifiers)

This is the ACTION layer — when other frameworks detect problems,
Fowler prescribes the specific named transformation.
"""

from __future__ import annotations

from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.tags import (
    DiagnosticTag,
    Framework,
    Recommendation,
    Severity,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LONG_METHOD_LINES = 30
_LONG_METHOD_CC = 10
_LONG_PARAM_LIST = 4
_LARGE_CLASS_METHODS = 20  # Not directly detectable per-function; class-level
_SWITCH_CC_THRESHOLD = 6


# ---------------------------------------------------------------------------
# Tag factory
# ---------------------------------------------------------------------------

def _tag(tag_id: str, severity: Severity, desc: str,
         recs: tuple[Recommendation, ...] = ()) -> DiagnosticTag:
    return DiagnosticTag(
        tag_id=tag_id,
        framework=Framework.FOWLER,
        severity=severity,
        description=desc,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Smell detectors
# ---------------------------------------------------------------------------

def analyze(result: MergedFunctionResult) -> list[DiagnosticTag]:
    """
    Run Fowler smell detection and refactoring recommendations.

    Args:
        result: Merged function data.

    Returns:
        List of applicable Fowler diagnostic tags with refactoring prescriptions.
    """
    tags: list[DiagnosticTag] = []
    m = result.metrics
    c = result.crap

    cc = m.cyclomatic_complexity
    lines = m.line_count
    params = m.parameter_count
    abc_b = m.abc_branches

    # --- SMELL-02: Long Method ---
    if lines > _LONG_METHOD_LINES or cc > _LONG_METHOD_CC:
        recs: list[Recommendation] = [
            Recommendation("Extract Method", "Name from comment intent, not implementation", 1),
        ]
        if params > 3:
            recs.append(Recommendation("Introduce Parameter Object", "Group related params", 2))
        if cc > 15:
            recs.append(Recommendation("Replace Method with Method Object", "Convert to class when temps block extraction", 3))
        if m.max_nesting_depth >= 3:
            recs.append(Recommendation("Decompose Conditional", "Simplify nested branches", 2))

        tags.append(_tag(
            "LONG_METHOD", Severity.WARNING,
            f"Long Method: {lines} lines, CC={cc}. "
            f"'Whenever we feel the need to comment something, we write a method instead.' — Fowler",
            tuple(recs),
        ))

    # --- SMELL-04: Long Parameter List ---
    if params > _LONG_PARAM_LIST:
        tags.append(_tag(
            "LONG_PARAM_LIST", Severity.WARNING,
            f"Long Parameter List: {params} parameters (threshold={_LONG_PARAM_LIST}). "
            f"High interface complexity.",
            (
                Recommendation("Introduce Parameter Object", "Group related params into dataclass", 1),
                Recommendation("Preserve Whole Object", "Pass object instead of extracting fields", 2),
                Recommendation("Replace Parameter with Method", "Derive param from known object", 3),
            ),
        ))

    # --- SMELL-10: Switch Statements / Conditional Chains ---
    # Approximation: high CC relative to nesting suggests conditional chains
    if cc >= _SWITCH_CC_THRESHOLD and m.max_nesting_depth <= 2 and cc > lines * 0.3:
        tags.append(_tag(
            "CONDITIONAL_CHAIN", Severity.WARNING,
            f"Likely conditional chain: CC={cc} with shallow nesting={m.max_nesting_depth}. "
            f"Multiple branches at same level suggest switch/elif pattern.",
            (
                Recommendation("Replace Conditional with Polymorphism",
                               "Distribute branches across polymorphic implementations", 1),
                Recommendation("Replace Parameter with Explicit Methods",
                               "If few stable cases", 2),
            ),
        ))

    # --- SMELL-22: Comments as Deodorant ---
    # Approximation: high cognitive complexity relative to ABC suggests
    # code that's hard to understand (would need comments to explain)
    if m.cognitive_complexity > 15 and cc > 8:
        tags.append(_tag(
            "COMMENTS_AS_DEODORANT", Severity.INFO,
            f"High cognitive complexity (CogC={m.cognitive_complexity}) suggests "
            f"code may rely on comments for understanding. "
            f"'First try to refactor so any comment becomes superfluous.' — Fowler",
            (
                Recommendation("Extract Method", "Name from comment intent", 1),
                Recommendation("Rename Method", "If method exists but name is unclear", 2),
                Recommendation("Introduce Assertion", "If commenting to state invariants", 3),
            ),
        ))

    # --- SMELL-07: Feature Envy ---
    # Approximation: high branch count (external calls) relative to assignments
    if abc_b > 0 and m.abc_assignments > 0:
        external_ratio = abc_b / (m.abc_assignments + abc_b)
        if external_ratio > 0.75 and abc_b > 5:
            tags.append(_tag(
                "FEATURE_ENVY", Severity.WARNING,
                f"Possible Feature Envy: {abc_b} calls vs {m.abc_assignments} assignments "
                f"({external_ratio:.0%} external). Method may belong elsewhere.",
                (
                    Recommendation("Move Method", "Move to the class it calls most", 1),
                    Recommendation("Extract Method", "Isolate envious part, then move", 2),
                ),
            ))

    # --- SMELL-12: Lazy Class (shallow, trivial) ---
    if lines <= 3 and cc <= 1 and abc_b <= 1:
        tags.append(_tag(
            "LAZY_CLASS", Severity.INFO,
            f"Minimal function: {lines} lines, CC={cc}. "
            f"Consider inlining if it adds no abstraction value.",
            (
                Recommendation("Inline Method", "Merge into caller if no abstraction value", 1),
            ),
        ))

    return tags


# ---------------------------------------------------------------------------
# Cross-framework refactoring mapping
# ---------------------------------------------------------------------------

# Maps tags from ANY framework to Fowler refactoring recommendations.
# Used by the reporting layer to provide unified action items.
REFACTORING_MAP: dict[str, tuple[Recommendation, ...]] = {
    # Feathers tags
    "MONSTER_SNARLED": (
        Recommendation("Replace Method with Method Object", "Convert to class to untangle state", 1),
        Recommendation("Decompose Conditional", "Simplify nested branches", 2),
    ),
    "MONSTER_BULLETED": (
        Recommendation("Extract Method", "One extraction per code section", 1),
    ),
    "LEGACY_DILEMMA": (
        Recommendation("Extract Interface", "Create Protocol for dependency injection", 1),
        Recommendation("Parameterize Constructor", "Break hard dependencies", 2),
    ),
    "SENSING_PROBLEM": (
        Recommendation("Separate Query from Modifier", "Split read from write", 1),
    ),
    # Ousterhout tags
    "SHALLOW_MODULE": (
        Recommendation("Inline Method", "Merge trivial wrappers into caller", 1),
    ),
    "PASS_THROUGH": (
        Recommendation("Inline Method", "Remove passthrough", 1),
        Recommendation("Remove Middle Man", "Expose delegate", 2),
    ),
    "OVEREXPOSED_API": (
        Recommendation("Hide Method", "Make rarely-used methods private", 1),
        Recommendation("Extract Interface", "Create focused interface per client", 2),
    ),
    "NONOBVIOUS": (
        Recommendation("Introduce Explaining Variable", "Name complex expressions", 1),
        Recommendation("Extract Method", "Name code sections by intent", 2),
    ),
    "COMPLEXITY_UPWARD": (
        Recommendation("Replace Exception with Test", "Eliminate exception for expected cases", 1),
        Recommendation("Introduce Null Object", "Remove null checks", 2),
    ),
    # Hunt & Thomas tags
    "BROKEN_WINDOW": (
        Recommendation("Extract Method", "Any improvement breaks the rot cycle", 1),
    ),
    "DRY_VIOLATION": (
        Recommendation("Extract Method", "Unify duplicated code", 1),
        Recommendation("Form Template Method", "If similar but not identical", 2),
    ),
    "COINCIDENCE_CODE": (
        Recommendation("Extract Method", "Name code sections to clarify intent", 1),
        Recommendation("Introduce Assertion", "Document assumptions explicitly", 2),
        Recommendation("Substitute Algorithm", "Replace with understood approach", 3),
    ),
    "GLOBAL_COUPLING": (
        Recommendation("Encapsulate Field", "Hide globals behind accessor", 1),
        Recommendation("Introduce Parameter Object", "Pass grouped globals as object", 2),
    ),
}


def get_refactorings_for_tag(tag_id: str) -> tuple[Recommendation, ...]:
    """Get Fowler refactoring recommendations for any framework's tag."""
    return REFACTORING_MAP.get(tag_id, ())
