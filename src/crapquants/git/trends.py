"""
Complexity trends — track how CRAP scores change over time.

Source: Adam Tornhill, Your Code as a Crime Scene (2024)

Classifies trends as:
    DETERIORATING, SLOWLY_DEGRADING, STABLE, SLOWLY_IMPROVING, IMPROVING
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendResult:
    """Complexity trend for a file."""

    file_path: str
    data_points: int
    earliest_crap: float
    latest_crap: float
    slope: float  # positive = getting worse
    trend: str  # DETERIORATING | SLOWLY_DEGRADING | STABLE | SLOWLY_IMPROVING | IMPROVING


def classify_trend(crap_history: list[float]) -> str:
    """
    Classify CRAP score trend from a list of scores over time.

    Args:
        crap_history: CRAP scores ordered oldest to newest.

    Returns:
        Trend classification string.
    """
    if len(crap_history) < 3:
        return "INSUFFICIENT_DATA"

    slope = _linear_slope(crap_history)

    if slope > 2.0:
        return "DETERIORATING"
    if slope > 0.5:
        return "SLOWLY_DEGRADING"
    if slope < -2.0:
        return "IMPROVING"
    if slope < -0.5:
        return "SLOWLY_IMPROVING"
    return "STABLE"


def compute_trend(
    file_path: str,
    crap_history: list[float],
) -> TrendResult:
    """
    Compute trend result for a file.

    Args:
        file_path: Path to file.
        crap_history: CRAP scores ordered oldest to newest.

    Returns:
        TrendResult with slope and classification.
    """
    if not crap_history:
        return TrendResult(
            file_path=file_path,
            data_points=0,
            earliest_crap=0.0,
            latest_crap=0.0,
            slope=0.0,
            trend="INSUFFICIENT_DATA",
        )

    slope = _linear_slope(crap_history) if len(crap_history) >= 3 else 0.0
    trend = classify_trend(crap_history)

    return TrendResult(
        file_path=file_path,
        data_points=len(crap_history),
        earliest_crap=crap_history[0],
        latest_crap=crap_history[-1],
        slope=round(slope, 3),
        trend=trend,
    )


def _linear_slope(values: list[float]) -> float:
    """
    Calculate simple linear regression slope.

    Uses ordinary least squares: slope = Σ((x-x̄)(y-ȳ)) / Σ((x-x̄)²)
    Where x = index position, y = CRAP score.
    """
    n = len(values)
    if n < 2:
        return 0.0

    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0

    return numerator / denominator
