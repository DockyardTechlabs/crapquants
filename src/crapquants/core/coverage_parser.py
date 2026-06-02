"""
Coverage data parser for coverage.py output formats.

Supports:
    - JSON (coverage json) — preferred, richest data
    - LCOV (coverage lcov) — widely supported
    - XML (coverage xml) — Cobertura format

Produces per-file line coverage data that the merge layer
joins with complexity data to compute CRAP scores.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class FileCoverage:
    """Coverage data for a single file."""

    file_path: str
    covered_lines: frozenset[int]
    missing_lines: frozenset[int]
    total_statements: int
    covered_statements: int
    coverage_percent: float  # 0.0 to 100.0


@dataclass(frozen=True)
class FunctionCoverage:
    """Coverage data for a single function within a file."""

    function_name: str
    file_path: str
    line_start: int
    line_end: int
    coverage_percent: float  # 0.0 to 100.0


def parse_coverage_json(json_path: str | Path) -> list[FileCoverage]:
    """
    Parse coverage.py JSON report.

    Generated via: pytest --cov=src --cov-report=json:coverage.json

    Args:
        json_path: Path to coverage.json file.

    Returns:
        List of FileCoverage, one per source file.

    Raises:
        FileNotFoundError: If JSON file doesn't exist.
        ValueError: If JSON format is unexpected.
    """
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Coverage JSON not found: {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))

    if "files" not in data:
        raise ValueError(
            f"Invalid coverage JSON format: 'files' key missing. "
            f"Expected coverage.py JSON output."
        )

    results: list[FileCoverage] = []

    for file_path, file_data in data["files"].items():
        summary = file_data.get("summary", {})
        executed = file_data.get("executed_lines", [])
        missing = file_data.get("missing_lines", [])
        total = summary.get("num_statements", 0)
        covered = summary.get("covered_lines", len(executed))
        pct = summary.get("percent_covered", 0.0)

        results.append(
            FileCoverage(
                file_path=file_path,
                covered_lines=frozenset(executed),
                missing_lines=frozenset(missing),
                total_statements=total,
                covered_statements=covered,
                coverage_percent=round(pct, 2),
            )
        )

    logger.info("coverage_parsed", format="json", files=len(results))
    return results


def parse_coverage_lcov(lcov_path: str | Path) -> list[FileCoverage]:
    """
    Parse LCOV coverage report.

    Generated via: pytest --cov=src --cov-report=lcov:coverage.lcov

    LCOV format:
        SF:<filepath>
        DA:<line>,<hit_count>
        LF:<total_lines>
        LH:<hit_lines>
        end_of_record

    Args:
        lcov_path: Path to LCOV file.

    Returns:
        List of FileCoverage, one per source file.
    """
    lcov_path = Path(lcov_path)
    if not lcov_path.exists():
        raise FileNotFoundError(f"LCOV file not found: {lcov_path}")

    content = lcov_path.read_text(encoding="utf-8")
    results: list[FileCoverage] = []

    current_file: str | None = None
    covered: set[int] = set()
    missing: set[int] = set()
    total_lines = 0
    hit_lines = 0

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("SF:"):
            current_file = line[3:]
            covered = set()
            missing = set()
            total_lines = 0
            hit_lines = 0

        elif line.startswith("DA:"):
            parts = line[3:].split(",")
            if len(parts) >= 2:
                line_num = int(parts[0])
                hits = int(parts[1])
                if hits > 0:
                    covered.add(line_num)
                else:
                    missing.add(line_num)

        elif line.startswith("LF:"):
            total_lines = int(line[3:])

        elif line.startswith("LH:"):
            hit_lines = int(line[3:])

        elif line == "end_of_record" and current_file:
            pct = (hit_lines / total_lines * 100.0) if total_lines > 0 else 0.0

            results.append(
                FileCoverage(
                    file_path=current_file,
                    covered_lines=frozenset(covered),
                    missing_lines=frozenset(missing),
                    total_statements=total_lines,
                    covered_statements=hit_lines,
                    coverage_percent=round(pct, 2),
                )
            )
            current_file = None

    logger.info("coverage_parsed", format="lcov", files=len(results))
    return results


def estimate_function_coverage(
    file_coverage: FileCoverage,
    function_name: str,
    line_start: int,
    line_end: int,
) -> FunctionCoverage:
    """
    Estimate coverage for a specific function within a file.

    Uses line-level coverage data to compute per-function coverage
    by intersecting the function's line range with covered/missing lines.

    Args:
        file_coverage: File-level coverage data.
        function_name: Name of the function.
        line_start: First line of the function.
        line_end: Last line of the function.

    Returns:
        FunctionCoverage with estimated coverage percentage.
    """
    func_lines = set(range(line_start, line_end + 1))
    all_statement_lines = file_coverage.covered_lines | file_coverage.missing_lines

    # Lines in this function that are statements (covered or missing)
    func_statements = func_lines & all_statement_lines

    if not func_statements:
        # No statement data for this function range — assume 0% (pessimistic)
        return FunctionCoverage(
            function_name=function_name,
            file_path=file_coverage.file_path,
            line_start=line_start,
            line_end=line_end,
            coverage_percent=0.0,
        )

    func_covered = func_lines & file_coverage.covered_lines
    pct = len(func_covered) / len(func_statements) * 100.0

    return FunctionCoverage(
        function_name=function_name,
        file_path=file_coverage.file_path,
        line_start=line_start,
        line_end=line_end,
        coverage_percent=round(pct, 2),
    )
