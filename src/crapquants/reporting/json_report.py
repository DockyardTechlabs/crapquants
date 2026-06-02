"""
JSON report generator for CRAPQuants.

Produces machine-readable JSON output with a versioned schema envelope.
Suitable for CI integration, dashboards, and programmatic consumption.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from crapquants.core.merge import MergedFileResult
from crapquants.frameworks.tags import DiagnosticTag


def generate_json_report(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
    phs_score: float | None = None,
    analysis_level: str = "standard",
    git_commit: str | None = None,
) -> dict[str, Any]:
    """
    Generate structured JSON report.

    Args:
        results: List of merged file results.
        all_tags: Dict mapping "file:func" to diagnostic tags.
        phs_score: Pragmatic Health Score.
        analysis_level: Analysis level used (quick/standard/deep/full).
        git_commit: Current git commit hash if available.

    Returns:
        Dict suitable for json.dumps().
    """
    total_functions = sum(len(r.functions) for r in results)
    crappy_count = sum(
        1 for r in results for f in r.functions if f.crap.is_crappy
    )
    all_crap_scores = [
        f.crap.crap_score for r in results for f in r.functions
    ]

    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tool": "crapquants",
        "tool_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_level": analysis_level,
        "git_commit": git_commit,
        "summary": {
            "files_analyzed": len(results),
            "functions_analyzed": total_functions,
            "crappy_functions": crappy_count,
            "crappy_percentage": round(
                crappy_count / max(total_functions, 1) * 100, 1
            ),
            "average_crap": round(
                sum(all_crap_scores) / max(len(all_crap_scores), 1), 2
            ),
            "max_crap": round(max(all_crap_scores, default=0.0), 2),
            "median_crap": round(
                _median(all_crap_scores), 2
            ) if all_crap_scores else 0.0,
            "pragmatic_health_score": phs_score,
        },
        "files": [],
    }

    # Include self-documenting glossary so consumers understand the schema
    from crapquants.reporting.glossary import build_glossary_json
    report["glossary"] = build_glossary_json()

    for file_result in results:
        file_entry: dict[str, Any] = {
            "path": file_result.file_path,
            "metrics": {
                "halstead_volume": file_result.file_metrics.halstead_volume,
                "halstead_difficulty": file_result.file_metrics.halstead_difficulty,
                "maintainability_index": file_result.file_metrics.maintainability_index,
                "total_lines": file_result.file_metrics.total_lines,
                "code_lines": file_result.file_metrics.code_lines,
            },
            "coverage_found": file_result.file_coverage is not None,
            "functions": [],
        }

        for func in file_result.functions:
            m = func.metrics
            c = func.crap
            tag_key = f"{file_result.file_path}:{m.name}"
            func_tags = all_tags.get(tag_key, [])

            func_entry: dict[str, Any] = {
                "name": m.name,
                "line_start": m.line_start,
                "line_end": m.line_end,
                "metrics": {
                    "cyclomatic_complexity": m.cyclomatic_complexity,
                    "cognitive_complexity": m.cognitive_complexity,
                    "abc_scalar": m.abc_scalar,
                    "abc_assignments": m.abc_assignments,
                    "abc_branches": m.abc_branches,
                    "abc_conditions": m.abc_conditions,
                    "line_count": m.line_count,
                    "max_nesting_depth": m.max_nesting_depth,
                    "parameter_count": m.parameter_count,
                },
                "coverage_percent": c.coverage,
                "crap_score": c.crap_score,
                "is_crappy": c.is_crappy,
                "crapload": c.crapload,
                "min_coverage_needed": c.min_coverage_needed,
                "tags": [
                    {
                        "tag_id": t.tag_id,
                        "framework": t.framework.value,
                        "severity": t.severity.value,
                        "description": t.description,
                        "recommendations": [
                            {"action": r.action, "rationale": r.rationale}
                            for r in t.recommendations
                        ],
                    }
                    for t in func_tags
                ],
            }
            file_entry["functions"].append(func_entry)

        report["files"].append(file_entry)

    return report


def write_json_report(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
    output_path: str,
    phs_score: float | None = None,
    analysis_level: str = "standard",
    git_commit: str | None = None,
) -> str:
    """
    Generate and write JSON report to file.

    Returns:
        Path to written file.
    """
    report = generate_json_report(
        results, all_tags, phs_score, analysis_level, git_commit
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return output_path


def _median(values: list[float]) -> float:
    """Calculate median of a list of numbers."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
    return sorted_vals[mid]
