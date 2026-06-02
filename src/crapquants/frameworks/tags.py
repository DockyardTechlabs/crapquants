"""
Shared diagnostic tag system for CRAPQuants frameworks.

Every framework produces DiagnosticTag instances. Tags carry:
    - A unique tag ID (e.g., MONSTER_SNARLED)
    - The source framework (Feathers, Ousterhout, etc.)
    - Severity level
    - Human-readable description
    - Recommended action(s)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Framework(str, Enum):
    """Source framework for a diagnostic tag."""

    FEATHERS = "Feathers"
    OUSTERHOUT = "Ousterhout"
    HUNT_THOMAS = "Hunt & Thomas"
    FOWLER = "Fowler"
    TORNHILL = "Tornhill"
    FORD = "Ford"


class Severity(str, Enum):
    """Tag severity levels."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Recommendation:
    """A specific refactoring or action recommendation."""

    action: str  # e.g., "Extract Method"
    rationale: str  # e.g., "One extraction per code section"
    priority: int = 0  # Lower = higher priority


@dataclass(frozen=True)
class DiagnosticTag:
    """A single diagnostic finding from a framework."""

    tag_id: str  # e.g., "MONSTER_SNARLED"
    framework: Framework
    severity: Severity
    description: str
    recommendations: tuple[Recommendation, ...] = ()


@dataclass
class FunctionDiagnostics:
    """All diagnostics for a single function, collected across frameworks."""

    function_name: str
    file_path: str
    line_number: int
    tags: list[DiagnosticTag] = field(default_factory=list)

    # Composite scores from each framework
    feathers_risk_score: float = 0.0  # FRS
    ousterhout_risk_score: float = 0.0  # ORS
    tornhill_behavioral_score: float = 0.0  # TBS
    cq_score: float = 0.0  # max(FRS, ORS, TBS)

    def add_tag(self, tag: DiagnosticTag) -> None:
        """Add a diagnostic tag."""
        self.tags.append(tag)

    @property
    def has_critical(self) -> bool:
        """Check if any tag is critical severity."""
        return any(t.severity == Severity.CRITICAL for t in self.tags)

    @property
    def tag_ids(self) -> list[str]:
        """Get list of tag IDs for quick lookup."""
        return [t.tag_id for t in self.tags]

    @property
    def highest_severity(self) -> Severity:
        """Return the highest severity among all tags."""
        if not self.tags:
            return Severity.INFO
        severity_order = [Severity.INFO, Severity.WARNING, Severity.HIGH, Severity.CRITICAL]
        max_idx = max(severity_order.index(t.severity) for t in self.tags)
        return severity_order[max_idx]
