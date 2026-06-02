"""
Tornhill Framework — Behavioral code analysis.

Source: Your Code as a Crime Scene, 2nd Ed (Adam Tornhill, 2024)

Provides:
    - TBS (Tornhill Behavioral Score): CRAP × activity × trend × knowledge risk
    - Hotspot detection (requires git history — Phase 6)
    - Static-only diagnostics available without git

Full git-based analysis (hotspots, change coupling, truck factor, trends)
is implemented in the git/ module (Phase 6). This module provides:
    1. Static diagnostics applicable without git
    2. TBS computation when git data is available
    3. Tag definitions for git-derived findings
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
# TBS computation (used when git data is available)
# ---------------------------------------------------------------------------

def compute_tbs(
    crap: float,
    change_frequency: int = 0,
    trend: str = "STABLE",
    truck_factor: int = 3,
    coupling_count: int = 0,
) -> float:
    """
    Tornhill Behavioral Score — CRAP amplified by behavioral signals.

    Args:
        crap: Base CRAP score.
        change_frequency: Number of commits touching this function.
        trend: Complexity trend (DETERIORATING/SLOWLY_DEGRADING/STABLE/SLOWLY_IMPROVING/IMPROVING).
        truck_factor: Minimum developers needed before knowledge loss.
        coupling_count: Number of files this function is change-coupled with.

    Returns:
        TBS score.
    """
    activity_weight = min(3.0, 1.0 + (change_frequency / 20.0))

    trend_weights = {
        "DETERIORATING": 1.5,
        "SLOWLY_DEGRADING": 1.2,
        "STABLE": 1.0,
        "SLOWLY_IMPROVING": 0.8,
        "IMPROVING": 0.6,
    }
    trend_weight = trend_weights.get(trend, 1.0)

    knowledge_weight = 1.0 + (1.0 / max(truck_factor, 1)) * 0.3
    coupling_weight = 1.0 + (coupling_count * 0.1)

    return round(crap * activity_weight * trend_weight * knowledge_weight * coupling_weight, 2)


# ---------------------------------------------------------------------------
# Tag factory
# ---------------------------------------------------------------------------

def _tag(tag_id: str, severity: Severity, desc: str,
         recs: tuple[Recommendation, ...] = ()) -> DiagnosticTag:
    return DiagnosticTag(
        tag_id=tag_id,
        framework=Framework.TORNHILL,
        severity=severity,
        description=desc,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Static analysis (available without git)
# ---------------------------------------------------------------------------

def analyze(result: MergedFunctionResult) -> list[DiagnosticTag]:
    """
    Run Tornhill static diagnostics (no git required).

    Full behavioral analysis (hotspots, coupling, truck factor) requires
    git history and is performed by the git/ module in Phase 6.
    This function provides baseline signals detectable from code alone.
    """
    tags: list[DiagnosticTag] = []
    m = result.metrics
    c = result.crap

    # --- Dormant hotspot candidate ---
    # High CRAP but untestable — if this ever changes, it's a time bomb
    if c.crap_score > 60 and c.coverage < 10:
        tags.append(_tag(
            "HOTSPOT_DORMANT", Severity.WARNING,
            f"Dormant hotspot candidate: CRAP={c.crap_score:.1f}, "
            f"coverage={c.coverage:.0f}%. "
            f"High risk if this code ever needs to change. "
            f"Monitor but deprioritize unless actively modified.",
            (
                Recommendation("Add to watchlist", "Flag for monitoring when git analysis is available", 1),
            ),
        ))

    # --- Knowledge silo risk ---
    # Complex code with high cognitive load — single developer likely understands it
    if m.cognitive_complexity > 20 and c.crap_score > 30:
        tags.append(_tag(
            "KNOWLEDGE_SILO", Severity.WARNING,
            f"Knowledge silo risk: CogC={m.cognitive_complexity}, "
            f"CRAP={c.crap_score:.1f}. "
            f"Code this complex likely understood by very few developers. "
            f"Confirm with git truck factor analysis (Level 3).",
            (
                Recommendation("Pair programming", "Share knowledge before it's lost", 1),
                Recommendation("Write documentation", "Capture design decisions", 2),
            ),
        ))

    return tags


# ---------------------------------------------------------------------------
# Git-aware analysis (Level 3+ — when git data is available)
# ---------------------------------------------------------------------------

@dataclass
class GitContext:
    """Git behavioral data for a single file, from Phase 6 git modules."""

    change_frequency: int = 0
    trend: str = "STABLE"  # From git/trends.py
    truck_factor: int = 3
    primary_author: str | None = None
    primary_ownership_pct: float = 0.0
    coupling_count: int = 0  # Number of files this file is change-coupled with
    hotspot_score: float = 0.0  # change_frequency × CRAP


def analyze_with_git(
    result: MergedFunctionResult,
    git_ctx: GitContext,
) -> list[DiagnosticTag]:
    """
    Run full Tornhill behavioral analysis with git history data.

    Layers git-derived tags on top of static analysis tags.
    Called when analysis level is 'deep' or 'full' and git history is available.

    Args:
        result: Merged function data.
        git_ctx: Git behavioral context for this file.

    Returns:
        List of diagnostic tags (static + behavioral).
    """
    # Start with static tags
    tags = analyze(result)
    m = result.metrics
    c = result.crap

    # --- Active hotspot (churn × CRAP) ---
    if git_ctx.change_frequency > 5 and c.crap_score > 30:
        tags.append(_tag(
            "HOTSPOT_ACTIVE", Severity.HIGH,
            f"Active hotspot: {git_ctx.change_frequency} commits × CRAP={c.crap_score:.1f} "
            f"= hotspot_score={git_ctx.hotspot_score:.0f}. "
            f"High complexity AND high change activity — priority refactoring target.",
            (
                Recommendation("Refactor this first", "Highest ROI — frequently touched + risky", 1),
                Recommendation("Write characterization tests", "Cover before changing", 2),
            ),
        ))

    # --- Complexity trend deteriorating ---
    if git_ctx.trend == "DETERIORATING":
        tags.append(_tag(
            "TREND_DETERIORATING", Severity.HIGH,
            f"Complexity trend: DETERIORATING. "
            f"CRAP score is increasing over recent commits. "
            f"Code is getting harder to maintain with each change.",
            (
                Recommendation("Intervene now", "Complexity will accelerate if not addressed", 1),
                Recommendation("Add complexity budget", "Set CRAP threshold as CI gate", 2),
            ),
        ))
    elif git_ctx.trend == "SLOWLY_DEGRADING":
        tags.append(_tag(
            "TREND_DEGRADING", Severity.WARNING,
            f"Complexity trend: SLOWLY DEGRADING. "
            f"Gradual complexity creep detected over recent commits.",
            (
                Recommendation("Monitor closely", "Will become critical if ignored", 1),
            ),
        ))

    # --- Knowledge silo (confirmed by git truck factor) ---
    if git_ctx.truck_factor <= 1 and c.crap_score > 20:
        tags.append(_tag(
            "KNOWLEDGE_SILO_CONFIRMED", Severity.CRITICAL,
            f"Knowledge silo CONFIRMED: truck_factor={git_ctx.truck_factor}, "
            f"primary_author={git_ctx.primary_author} "
            f"({git_ctx.primary_ownership_pct:.0%} ownership). "
            f"If this developer leaves, CRAP={c.crap_score:.1f} code becomes unmaintainable.",
            (
                Recommendation("Pair programming sessions", "Transfer knowledge immediately", 1),
                Recommendation("Write architectural decision records", "Document the WHY", 2),
                Recommendation("Add comprehensive tests", "Tests ARE documentation", 3),
            ),
        ))

    # --- Change coupling (implicit dependency) ---
    if git_ctx.coupling_count > 2:
        tags.append(_tag(
            "CHANGE_COUPLED", Severity.WARNING,
            f"Change-coupled with {git_ctx.coupling_count} other files. "
            f"This file frequently changes together with other files — "
            f"possible hidden dependency, copy-paste, or shotgun surgery.",
            (
                Recommendation("Investigate coupling", "Check if modules share a responsibility", 1),
                Recommendation("Extract shared logic", "If DRY violation, unify into one module", 2),
            ),
        ))

    # --- Churn hotspot (high change frequency even without high CRAP) ---
    if git_ctx.change_frequency > 20 and c.crap_score <= 30:
        tags.append(_tag(
            "CHURN_HOTSPOT", Severity.INFO,
            f"High churn: {git_ctx.change_frequency} commits but CRAP={c.crap_score:.1f} (OK). "
            f"Frequently changed but manageable — good candidate for stability investment.",
            (
                Recommendation("Increase test coverage", "Protect high-traffic code", 1),
            ),
        ))

    return tags
