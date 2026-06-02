"""
Baseline compare — detects regressions by comparing current vs saved baseline.

Identifies:
    - New CRAPpy functions (were clean, now CRAPpy)
    - Worsened functions (CRAP increased)
    - Improved functions (CRAP decreased)
    - Removed functions (in baseline but not in current)
    - New functions (in current but not in baseline)
    - Aggregate CRAP regression (total CRAP increased)

Usage:
    crapquants analyze ./src --baseline data/baseline.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from crapquants.core.merge import MergedFileResult

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class FunctionDelta:
    """Change in a single function between baseline and current."""

    file: str
    function: str
    baseline_crap: float
    current_crap: float
    delta: float  # current - baseline (positive = worse)
    baseline_cc: int
    current_cc: int
    baseline_coverage: float
    current_coverage: float
    status: str  # "worsened" | "improved" | "new_crappy" | "fixed" | "unchanged" | "new" | "removed"


@dataclass
class ComparisonResult:
    """Complete comparison between baseline and current analysis."""

    baseline_path: str
    baseline_commit: str | None
    baseline_aggregate_crap: float
    current_aggregate_crap: float
    aggregate_delta: float  # positive = regression

    total_baseline_functions: int
    total_current_functions: int

    new_crappy: list[FunctionDelta] = field(default_factory=list)
    worsened: list[FunctionDelta] = field(default_factory=list)
    improved: list[FunctionDelta] = field(default_factory=list)
    fixed: list[FunctionDelta] = field(default_factory=list)
    new_functions: list[FunctionDelta] = field(default_factory=list)
    removed_functions: list[FunctionDelta] = field(default_factory=list)

    @property
    def is_regression(self) -> bool:
        """True if any regression detected (new CRAPpy or aggregate increase)."""
        return len(self.new_crappy) > 0 or self.aggregate_delta > 0

    @property
    def summary(self) -> str:
        """Human-readable summary of changes."""
        parts = []
        if self.new_crappy:
            parts.append(f"{len(self.new_crappy)} new CRAPpy")
        if self.worsened:
            parts.append(f"{len(self.worsened)} worsened")
        if self.improved:
            parts.append(f"{len(self.improved)} improved")
        if self.fixed:
            parts.append(f"{len(self.fixed)} fixed")
        if self.new_functions:
            parts.append(f"{len(self.new_functions)} new")
        if self.removed_functions:
            parts.append(f"{len(self.removed_functions)} removed")

        delta_str = f"+{self.aggregate_delta:.1f}" if self.aggregate_delta > 0 else f"{self.aggregate_delta:.1f}"
        status = "REGRESSION" if self.is_regression else "OK"

        return f"[{status}] Aggregate CRAP: {delta_str} | " + ", ".join(parts)


def load_baseline(baseline_path: str | Path) -> dict[str, Any]:
    """
    Load a saved baseline file.

    Args:
        baseline_path: Path to baseline JSON.

    Returns:
        Parsed baseline dict.

    Raises:
        FileNotFoundError: If baseline doesn't exist.
        ValueError: If baseline format is invalid.
    """
    baseline_path = Path(baseline_path)
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline not found: {baseline_path}")

    data = json.loads(baseline_path.read_text(encoding="utf-8"))

    if "entries" not in data or "schema_version" not in data:
        raise ValueError(f"Invalid baseline format: missing required keys")

    return data


def compare(
    results: list[MergedFileResult],
    baseline_path: str | Path,
    crap_threshold: float = 30.0,
) -> ComparisonResult:
    """
    Compare current analysis results against a saved baseline.

    Args:
        results: Current merged analysis results.
        baseline_path: Path to baseline JSON file.
        crap_threshold: CRAP threshold for "CRAPpy" classification.

    Returns:
        ComparisonResult with all detected changes.
    """
    baseline = load_baseline(baseline_path)

    # Build lookup from baseline: key = "file:function:line"
    # Including line disambiguates same-named methods within one file
    # (e.g. multiple classes each defining visit_Call). Without it,
    # entries collapse and the aggregate is undercounted.
    baseline_lookup: dict[str, dict[str, Any]] = {}
    for entry in baseline["entries"]:
        key = f"{entry['file']}:{entry['function']}:{entry.get('line', 0)}"
        baseline_lookup[key] = entry

    # Build lookup from current results (same key scheme)
    current_lookup: dict[str, dict[str, Any]] = {}
    for file_result in results:
        for func in file_result.functions:
            m = func.metrics
            c = func.crap
            key = f"{file_result.file_path}:{m.name}:{m.line_start}"
            current_lookup[key] = {
                "file": file_result.file_path,
                "function": m.name,
                "cc": m.cyclomatic_complexity,
                "cogc": m.cognitive_complexity,
                "coverage": c.coverage,
                "crap_score": c.crap_score,
                "is_crappy": c.is_crappy,
            }

    # Compute aggregate CRAP
    baseline_aggregate = baseline.get("aggregate_crap", 0.0)
    current_aggregate = round(sum(e["crap_score"] for e in current_lookup.values()), 2)

    comparison = ComparisonResult(
        baseline_path=str(baseline_path),
        baseline_commit=baseline.get("git_commit"),
        baseline_aggregate_crap=baseline_aggregate,
        current_aggregate_crap=current_aggregate,
        aggregate_delta=round(current_aggregate - baseline_aggregate, 2),
        total_baseline_functions=len(baseline_lookup),
        total_current_functions=len(current_lookup),
    )

    # Compare functions present in both
    all_keys = set(baseline_lookup.keys()) | set(current_lookup.keys())

    for key in sorted(all_keys):
        bl = baseline_lookup.get(key)
        cur = current_lookup.get(key)

        if bl and cur:
            delta = round(cur["crap_score"] - bl["crap_score"], 2)
            fd = FunctionDelta(
                file=cur["file"],
                function=cur["function"],
                baseline_crap=bl["crap_score"],
                current_crap=cur["crap_score"],
                delta=delta,
                baseline_cc=bl["cc"],
                current_cc=cur["cc"],
                baseline_coverage=bl["coverage"],
                current_coverage=cur["coverage"],
                status="unchanged",
            )

            if not bl["is_crappy"] and cur["is_crappy"]:
                fd = FunctionDelta(**{**fd.__dict__, "status": "new_crappy"})
                comparison.new_crappy.append(fd)
            elif bl["is_crappy"] and not cur["is_crappy"]:
                fd = FunctionDelta(**{**fd.__dict__, "status": "fixed"})
                comparison.fixed.append(fd)
            elif delta > 1.0:
                fd = FunctionDelta(**{**fd.__dict__, "status": "worsened"})
                comparison.worsened.append(fd)
            elif delta < -1.0:
                fd = FunctionDelta(**{**fd.__dict__, "status": "improved"})
                comparison.improved.append(fd)

        elif cur and not bl:
            # New function not in baseline
            fd = FunctionDelta(
                file=cur["file"], function=cur["function"],
                baseline_crap=0.0, current_crap=cur["crap_score"],
                delta=cur["crap_score"],
                baseline_cc=0, current_cc=cur["cc"],
                baseline_coverage=0.0, current_coverage=cur["coverage"],
                status="new",
            )
            comparison.new_functions.append(fd)

        elif bl and not cur:
            # Function removed
            fd = FunctionDelta(
                file=bl["file"], function=bl["function"],
                baseline_crap=bl["crap_score"], current_crap=0.0,
                delta=-bl["crap_score"],
                baseline_cc=bl["cc"], current_cc=0,
                baseline_coverage=bl["coverage"], current_coverage=0.0,
                status="removed",
            )
            comparison.removed_functions.append(fd)

    logger.info(
        "baseline_compared",
        baseline=str(baseline_path),
        regression=comparison.is_regression,
        aggregate_delta=comparison.aggregate_delta,
        new_crappy=len(comparison.new_crappy),
        worsened=len(comparison.worsened),
        improved=len(comparison.improved),
        fixed=len(comparison.fixed),
    )

    return comparison
