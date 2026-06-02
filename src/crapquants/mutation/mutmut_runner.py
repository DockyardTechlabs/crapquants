"""
Mutmut integration — optional mutation testing (Level 4).

Invokes mutmut CLI via subprocess and parses its results to produce
a mutation score per file. Mutation testing reveals test quality:
if a mutant survives (test still passes after code change), the test
suite has a blind spot.

mutmut is NOT a Python dependency of CRAPQuants — it's a system tool
invoked via subprocess, same pattern as Semgrep.

Mutation Score = killed_mutants / total_mutants × 100
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MutantResult:
    """Result for a single mutant."""

    id: int
    status: str  # "killed" | "survived" | "timeout" | "suspicious" | "skipped"
    file_path: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class MutationReport:
    """Mutation testing results for a target."""

    total_mutants: int
    killed: int
    survived: int
    timeout: int
    suspicious: int
    skipped: int
    mutation_score: float  # 0.0 to 100.0
    survived_mutants: list[MutantResult]


def is_mutmut_available() -> bool:
    """Check if mutmut CLI is installed."""
    return shutil.which("mutmut") is not None


def run_mutmut(
    source_path: str | Path,
    test_command: str = "pytest",
    timeout_per_mutant: int = 30,
    max_mutants: int = 100,
    runner_timeout: int = 600,
) -> MutationReport | None:
    """
    Run mutmut mutation testing.

    Args:
        source_path: Python file or directory to mutate.
        test_command: Test runner command (e.g., "pytest tests/").
        timeout_per_mutant: Seconds per mutant before timeout.
        max_mutants: Maximum mutants to generate (limits runtime).
        runner_timeout: Total timeout for entire mutmut run.

    Returns:
        MutationReport with results, or None if mutmut unavailable/failed.
    """
    if not is_mutmut_available():
        logger.info(
            "mutmut_not_installed",
            message="mutmut not found. Install with: pip install mutmut",
        )
        return None

    source_path = Path(source_path)

    # Step 1: Run mutmut
    cmd = [
        "mutmut", "run",
        "--paths-to-mutate", str(source_path),
        "--runner", test_command,
        "--no-progress",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=runner_timeout,
        )
    except subprocess.TimeoutExpired:
        logger.error("mutmut_timeout", timeout=runner_timeout)
        return None
    except FileNotFoundError:
        logger.error("mutmut_not_found")
        return None

    # mutmut exits 0 on success (all killed) or 2 (survivors exist)
    if result.returncode not in (0, 2):
        logger.warning("mutmut_error", returncode=result.returncode, stderr=result.stderr[:300])
        # Still try to parse results

    # Step 2: Get results via mutmut results
    return _get_results()


def _get_results() -> MutationReport | None:
    """Parse mutmut results from `mutmut results` command."""
    try:
        result = subprocess.run(
            ["mutmut", "results"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    return _parse_results_output(result.stdout)


def _parse_results_output(output: str) -> MutationReport:
    """
    Parse mutmut results text output.

    mutmut results output format:
        To apply a mutant on disk:
            mutmut apply <id>
        To show a mutant:
            mutmut show <id>

        Survived 🙁 (3)
        ---- src/module.py (line 15) ----
        3

        Killed (10)
        ...
    """
    killed = 0
    survived = 0
    timeout = 0
    suspicious = 0
    skipped = 0
    survived_mutants: list[MutantResult] = []

    current_section = ""

    for line in output.splitlines():
        line = line.strip()

        if line.startswith("Survived"):
            current_section = "survived"
            # Extract count from "Survived 🙁 (3)"
            count = _extract_count(line)
            if count is not None:
                survived = count
        elif line.startswith("Killed"):
            current_section = "killed"
            count = _extract_count(line)
            if count is not None:
                killed = count
        elif line.startswith("Timeout"):
            current_section = "timeout"
            count = _extract_count(line)
            if count is not None:
                timeout = count
        elif line.startswith("Suspicious"):
            current_section = "suspicious"
            count = _extract_count(line)
            if count is not None:
                suspicious = count
        elif line.startswith("Skipped"):
            current_section = "skipped"
            count = _extract_count(line)
            if count is not None:
                skipped = count
        elif current_section == "survived" and line.startswith("----"):
            # Parse "---- src/module.py (line 15) ----"
            parts = line.strip("-").strip()
            file_path = None
            line_num = None
            if "(line" in parts:
                fp_part, line_part = parts.rsplit("(line", 1)
                file_path = fp_part.strip()
                try:
                    line_num = int(line_part.strip().rstrip(")"))
                except ValueError:
                    pass
            survived_mutants.append(MutantResult(
                id=len(survived_mutants) + 1,
                status="survived",
                file_path=file_path,
                line=line_num,
            ))

    total = killed + survived + timeout + suspicious + skipped
    score = (killed / total * 100.0) if total > 0 else 0.0

    return MutationReport(
        total_mutants=total,
        killed=killed,
        survived=survived,
        timeout=timeout,
        suspicious=suspicious,
        skipped=skipped,
        mutation_score=round(score, 1),
        survived_mutants=survived_mutants,
    )


def _extract_count(line: str) -> int | None:
    """Extract count from a line like 'Killed (10)' or 'Survived 🙁 (3)'."""
    try:
        # Find last parenthesized number
        if "(" in line and ")" in line:
            count_str = line.rsplit("(", 1)[1].split(")")[0].strip()
            return int(count_str)
    except (ValueError, IndexError):
        pass
    return None


def format_mutation_summary(report: MutationReport) -> str:
    """Format mutation report as human-readable summary."""
    lines = [
        f"Mutation Score: {report.mutation_score:.1f}%",
        f"  Total mutants: {report.total_mutants}",
        f"  Killed: {report.killed}",
        f"  Survived: {report.survived}",
        f"  Timeout: {report.timeout}",
    ]

    if report.survived_mutants:
        lines.append("")
        lines.append("Surviving mutants (test blind spots):")
        for m in report.survived_mutants[:10]:
            loc = f"{m.file_path}:{m.line}" if m.file_path and m.line else f"mutant #{m.id}"
            lines.append(f"  - {loc}")

    return "\n".join(lines)
