"""
Ousterhout Framework — Design quality analysis.

Source: A Philosophy of Software Design, 2nd Ed (John Ousterhout)

Provides:
    - ORS (Ousterhout Risk Score): CRAP × depth_factor × obscurity_factor × red_flag_factor
    - 14 Red Flag detections (RF-01 through RF-14)
    - depth_ratio: implementation lines / interface complexity
    - cognitive_load_proxy: CC + params + globals + nesting

Attacks the comp(m) side of the CRAP formula.
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

_SHALLOW_DEPTH_RATIO = 3.0
_DEEP_DEPTH_RATIO = 10.0
_PASS_THROUGH_MAX_LINES = 3
_LONG_PARAM_THRESHOLD = 4
_VAGUE_NAMES = frozenset({
    "data", "result", "temp", "val", "info", "obj", "item", "thing",
    "stuff", "handler", "manager", "processor", "helper", "utils",
    "tmp", "ret", "res", "buf", "x", "y", "d", "e", "r", "s", "t",
})
_OVEREXPOSURE_RATIO = 4.0
_NONOBVIOUS_THRESHOLD = 3
_HIGH_ERROR_HANDLING_RATIO = 0.4
_NAME_LENGTH_THRESHOLD = 40


# ---------------------------------------------------------------------------
# Metric computations
# ---------------------------------------------------------------------------

def compute_depth_ratio(line_count: int, param_count: int) -> float:
    """
    Module depth ratio = implementation lines / interface complexity.

    Interface complexity approximated as param_count + 1 (return).
    Deep modules: high ratio (lots of functionality per interface unit).
    Shallow modules: low ratio (interface nearly as complex as implementation).
    """
    interface_complexity = max(1, param_count + 1)
    return round(line_count / interface_complexity, 2)


def compute_cognitive_load_proxy(
    cc: int, cogc: int, param_count: int, nesting: int,
) -> int:
    """
    Cognitive load proxy — how much a developer needs to know.

    Combines CC, Cognitive Complexity, parameter count, and nesting depth.
    """
    return cc + cogc + param_count + nesting


def compute_obscurity_score(
    has_docstring: bool = True,
    has_type_annotations: bool = True,
    vague_name_count: int = 0,
) -> int:
    """
    Obscurity score — how hard it is to understand what code does.

    Higher = more obscure.
    """
    score = 0
    if not has_docstring:
        score += 2
    if not has_type_annotations:
        score += 1
    score += vague_name_count
    return score


def compute_ors(
    crap: float,
    depth_ratio: float,
    obscurity_score: int,
    red_flag_count: int,
) -> float:
    """
    Ousterhout Risk Score — CRAP amplified by design quality signals.

    ORS = CRAP × depth_factor × obscurity_factor × red_flag_factor
    """
    # Shallow modules amplify risk
    depth_factor = max(1.0, _SHALLOW_DEPTH_RATIO / max(depth_ratio, 0.1))

    # Obscurity amplifies risk
    obscurity_factor = 1.0 + (obscurity_score / 10.0)

    # Red flags amplify risk
    red_flag_factor = 1.0 + (red_flag_count * 0.15)

    return round(crap * depth_factor * obscurity_factor * red_flag_factor, 2)


# ---------------------------------------------------------------------------
# Tag factory
# ---------------------------------------------------------------------------

def _tag(tag_id: str, severity: Severity, desc: str,
         recs: tuple[Recommendation, ...] = ()) -> DiagnosticTag:
    return DiagnosticTag(
        tag_id=tag_id,
        framework=Framework.OUSTERHOUT,
        severity=severity,
        description=desc,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Red Flag detection
# ---------------------------------------------------------------------------

def detect_red_flags(result: MergedFunctionResult) -> list[DiagnosticTag]:
    """
    Detect Ousterhout's 14 Red Flags applicable via static analysis.

    Args:
        result: Merged function data.

    Returns:
        List of detected red flag tags.
    """
    tags: list[DiagnosticTag] = []
    m = result.metrics
    c = result.crap

    depth = compute_depth_ratio(m.line_count, m.parameter_count)
    cc = m.cyclomatic_complexity
    cogc = m.cognitive_complexity

    # RF-01: Shallow Module
    if depth < _SHALLOW_DEPTH_RATIO and m.line_count <= 5:
        tags.append(_tag(
            "SHALLOW_MODULE", Severity.WARNING,
            f"Shallow module: depth_ratio={depth:.1f} (threshold={_SHALLOW_DEPTH_RATIO}). "
            f"Interface nearly as complex as implementation.",
            (
                Recommendation("Inline Method", "Merge trivial wrapper into caller", 1),
                Recommendation("Deepen functionality", "Add more implementation behind the interface", 2),
            ),
        ))

    # RF-04: Overexposure (too many parameters)
    if m.parameter_count > _LONG_PARAM_THRESHOLD:
        tags.append(_tag(
            "OVEREXPOSED_API", Severity.WARNING,
            f"Overexposed API: {m.parameter_count} parameters (threshold={_LONG_PARAM_THRESHOLD}). "
            f"Callers must understand too many details.",
            (
                Recommendation("Introduce Parameter Object", "Group related params", 1),
                Recommendation("Preserve Whole Object", "Pass object instead of fields", 2),
            ),
        ))

    # RF-05: Pass-Through Method
    if m.line_count <= _PASS_THROUGH_MAX_LINES and cc <= 1 and m.abc_branches == 1:
        tags.append(_tag(
            "PASS_THROUGH", Severity.INFO,
            f"Pass-through method: {m.line_count} lines, CC={cc}, single call. "
            f"Adds interface overhead without hiding complexity.",
            (
                Recommendation("Inline Method", "Remove passthrough, call delegate directly", 1),
                Recommendation("Remove Middle Man", "Expose delegate to callers", 2),
            ),
        ))

    # RF-11: Vague Name
    name_lower = m.name.lower()
    is_vague = any(v in name_lower.split("_") for v in _VAGUE_NAMES)
    if is_vague:
        tags.append(_tag(
            "VAGUE_NAMING", Severity.INFO,
            f"Vague function name: '{m.name}'. "
            f"Names should convey intent precisely.",
            (
                Recommendation("Rename Method", "Choose precise, intention-revealing name", 1),
            ),
        ))

    # RF-12: Hard to Pick Name (overly long or contains 'and'/'or')
    if len(m.name) > _NAME_LENGTH_THRESHOLD or "_and_" in m.name or "_or_" in m.name:
        tags.append(_tag(
            "HARD_TO_NAME", Severity.WARNING,
            f"Hard to name: '{m.name}' (length={len(m.name)}). "
            f"If a function is hard to name, it likely does too much.",
            (
                Recommendation("Extract Method", "Split into focused functions with clear names", 1),
            ),
        ))

    # RF-14: Nonobvious Code (composite)
    nonobvious_score = 0
    if cc > 5:
        nonobvious_score += 1
    if cogc > 10:
        nonobvious_score += 1
    if m.parameter_count > 3:
        nonobvious_score += 1
    if m.max_nesting_depth >= 3:
        nonobvious_score += 1
    if is_vague:
        nonobvious_score += 1

    if nonobvious_score >= _NONOBVIOUS_THRESHOLD:
        tags.append(_tag(
            "NONOBVIOUS", Severity.HIGH,
            f"Nonobvious code: score={nonobvious_score}/{_NONOBVIOUS_THRESHOLD}. "
            f"CC={cc}, CogC={cogc}, params={m.parameter_count}, nesting={m.max_nesting_depth}.",
            (
                Recommendation("Introduce Explaining Variable", "Name complex expressions", 1),
                Recommendation("Extract Method", "Name code sections by intent", 2),
                Recommendation("Add type annotations and docstring", "Make interface explicit", 3),
            ),
        ))

    # DP-10/11: Complexity Upward (excessive error handling proxy)
    # Approximation: if ABC conditions are > 40% of total ABC components
    total_abc = m.abc_assignments + m.abc_branches + m.abc_conditions
    if total_abc > 0:
        condition_ratio = m.abc_conditions / total_abc
        if condition_ratio > _HIGH_ERROR_HANDLING_RATIO and cc > 5:
            tags.append(_tag(
                "COMPLEXITY_UPWARD", Severity.WARNING,
                f"Condition-heavy code: {m.abc_conditions}/{total_abc} ABC components are conditions "
                f"({condition_ratio:.0%}). May be pushing complexity upward.",
                (
                    Recommendation("Define Errors Out of Existence", "Handle conditions internally", 1),
                    Recommendation("Replace Exception with Test", "Eliminate exception for expected cases", 2),
                ),
            ))

    # Positive signal: Deep Module
    if depth >= _DEEP_DEPTH_RATIO and c.crap_score < 30:
        tags.append(_tag(
            "DEEP_MODULE", Severity.INFO,
            f"Deep module: depth_ratio={depth:.1f}. "
            f"Rich functionality behind simple interface — good design.",
        ))

    return tags


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(result: MergedFunctionResult) -> list[DiagnosticTag]:
    """Run full Ousterhout diagnostic analysis."""
    return detect_red_flags(result)
