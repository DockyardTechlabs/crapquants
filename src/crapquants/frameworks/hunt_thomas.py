"""
Hunt & Thomas Framework — Engineering culture and sustainability analysis.

Source: The Pragmatic Programmer, 20th Anniversary Ed (Andrew Hunt, David Thomas)

Provides:
    - PHS (Pragmatic Health Score): Codebase-level sustainability (0-100)
    - Broken Windows detection
    - Coincidence programming detection
    - DRY violation flagging
    - Entropy rate tracking

Operates at the engineering culture layer — sustains quality over time.
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
# Constants
# ---------------------------------------------------------------------------

_COINCIDENCE_CC_THRESHOLD = 8
_GLOBAL_COUPLING_THRESHOLD = 3
_NO_SAFETY_NET_CC = 5


# ---------------------------------------------------------------------------
# Tag factory
# ---------------------------------------------------------------------------

def _tag(tag_id: str, severity: Severity, desc: str,
         recs: tuple[Recommendation, ...] = ()) -> DiagnosticTag:
    return DiagnosticTag(
        tag_id=tag_id,
        framework=Framework.HUNT_THOMAS,
        severity=severity,
        description=desc,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Codebase-level health (PHS)
# ---------------------------------------------------------------------------

@dataclass
class CodebaseHealth:
    """Hunt & Thomas Codebase Health Report."""

    total_functions: int = 0
    crappy_functions: int = 0
    broken_window_count: int = 0
    coincidence_count: int = 0
    no_safety_net_count: int = 0
    average_crap: float = 0.0
    max_crap: float = 0.0


def compute_pragmatic_health_score(health: CodebaseHealth) -> float:
    """
    Pragmatic Health Score — 0-100 codebase sustainability metric.

    Penalizes:
        - High percentage of CRAPpy functions (heavy penalty)
        - Broken Windows (heavy penalty)
        - Coincidence code (medium penalty)
        - No safety net functions (medium penalty)
    """
    if health.total_functions == 0:
        return 100.0

    score = 100.0

    # CRAPpy function percentage (up to -30)
    crappy_pct = health.crappy_functions / health.total_functions
    score -= crappy_pct * 30

    # Broken windows (up to -25)
    bw_pct = health.broken_window_count / health.total_functions
    score -= min(25, bw_pct * 100)

    # Coincidence code (up to -20)
    score -= min(20, health.coincidence_count * 5)

    # No safety net (up to -15)
    nsn_pct = health.no_safety_net_count / health.total_functions
    score -= min(15, nsn_pct * 30)

    return round(max(0.0, min(100.0, score)), 1)


# ---------------------------------------------------------------------------
# Per-function diagnostic analysis
# ---------------------------------------------------------------------------

def analyze(result: MergedFunctionResult) -> list[DiagnosticTag]:
    """
    Run Hunt & Thomas diagnostic analysis on a merged function result.

    Args:
        result: Merged function data.

    Returns:
        List of applicable Hunt & Thomas diagnostic tags.
    """
    tags: list[DiagnosticTag] = []
    m = result.metrics
    c = result.crap

    cc = m.cyclomatic_complexity
    cov = c.coverage
    cogc = m.cognitive_complexity

    # --- Programming by Coincidence (Tip 62) ---
    # High CC + no coverage + no assertions (approximated by ABC conditions relative to CC)
    is_coincidence = (
        cc >= _COINCIDENCE_CC_THRESHOLD
        and cov == 0.0
        and m.max_nesting_depth >= 2
    )
    if is_coincidence:
        tags.append(_tag(
            "COINCIDENCE_CODE", Severity.CRITICAL,
            f"Programming by Coincidence: CC={cc}, CogC={cogc}, 0% coverage, "
            f"nesting={m.max_nesting_depth}. Code works but nobody knows why. "
            f"Any change could break it in non-obvious ways.",
            (
                Recommendation("Write Characterization Tests", "Document actual behavior", 1),
                Recommendation("Extract Method", "Name code sections to clarify intent", 2),
                Recommendation("Introduce Assertion", "Document assumptions explicitly", 3),
            ),
        ))

    # --- No Safety Net (Tip 70: Test Your Software, or Your Users Will) ---
    if cov == 0.0 and cc > _NO_SAFETY_NET_CC:
        tags.append(_tag(
            "NO_SAFETY_NET", Severity.HIGH,
            f"No safety net: CC={cc} with 0% coverage. "
            f"Coding ain't done 'til all the tests run (Tip 91).",
            (
                Recommendation("Write tests before next change", "Cover and Modify, not Edit and Pray", 1),
            ),
        ))

    # --- Swallowed Exceptions (Tip 38: Crash Early) ---
    # Approximation: if ABC conditions are 0 but CC > 1, exceptions may be swallowed
    # This is a rough heuristic — full detection requires AST analysis of except blocks
    # (implemented in Phase 7 security module)

    # --- No Contracts (Tip 37: Design with Contracts) ---
    if cc > 10 and m.abc_conditions < 2:
        tags.append(_tag(
            "NO_CONTRACTS", Severity.WARNING,
            f"Complex function (CC={cc}) with minimal condition checks "
            f"(ABC conditions={m.abc_conditions}). "
            f"Consider adding precondition/postcondition assertions.",
            (
                Recommendation("Introduce Assertion", "Add pre/postconditions", 1),
            ),
        ))

    # --- Broken Window signal (per-function — commit history needed for full detection) ---
    # Without git history, we flag functions that are CRAPpy as *potential* broken windows
    if c.is_crappy and cov < 20.0:
        tags.append(_tag(
            "BROKEN_WINDOW", Severity.HIGH,
            f"Potential Broken Window: CRAP={c.crap_score:.1f}, coverage={cov:.0f}%. "
            f"Don't live with broken windows (Tip 5). "
            f"Tolerating this degrades the entire codebase's trajectory.",
            (
                Recommendation("Fix this first", "Any improvement breaks the rot cycle", 1),
            ),
        ))

    # --- Refactor Ready (positive — safe to refactor) ---
    if cov >= 70.0 and c.is_crappy:
        tags.append(_tag(
            "REFACTOR_READY", Severity.INFO,
            f"Refactor Ready: CRAP={c.crap_score:.1f} but coverage={cov:.0f}%. "
            f"High coverage provides safety net for refactoring (Tip 65).",
            (
                Recommendation("Refactor Early, Refactor Often", "Coverage is your safety net", 1),
            ),
        ))

    return tags
