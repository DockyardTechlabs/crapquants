"""
GitHub Actions annotation reporter for CRAPQuants.

Produces GitHub Actions workflow commands (::warning, ::error)
that show inline annotations on PR diff views.

Format: ::warning file={name},line={line},endLine={endLine},title={title}::{message}
"""

from __future__ import annotations

from crapquants.core.merge import MergedFileResult
from crapquants.frameworks.tags import DiagnosticTag, Severity


def _severity_to_gha_level(severity: Severity) -> str:
    """Map severity to GitHub Actions annotation level."""
    if severity in (Severity.CRITICAL, Severity.HIGH):
        return "error"
    if severity == Severity.WARNING:
        return "warning"
    return "notice"


def generate_annotations(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
    crap_threshold: float = 30.0,
) -> list[str]:
    """
    Generate GitHub Actions annotation commands.

    Args:
        results: List of merged file results.
        all_tags: Dict mapping "file:func" to diagnostic tags.
        crap_threshold: CRAP threshold for annotations.

    Returns:
        List of GitHub Actions annotation command strings.
    """
    annotations: list[str] = []

    for file_result in results:
        for func in file_result.functions:
            m = func.metrics
            c = func.crap

            # CRAP threshold violation
            if c.is_crappy:
                msg = (
                    f"CRAP={c.crap_score:.1f} (CC={m.cyclomatic_complexity}, "
                    f"Coverage={c.coverage:.0f}%). "
                    f"Need coverage >= {c.min_coverage_needed:.0f}% or reduce CC."
                )
                annotations.append(
                    f"::warning file={file_result.file_path},"
                    f"line={m.line_start},endLine={m.line_end},"
                    f"title=CRAPQuants: CRAP threshold exceeded::{msg}"
                )

            # Framework tag annotations
            tag_key = f"{file_result.file_path}:{m.name}"
            func_tags = all_tags.get(tag_key, [])

            for tag in func_tags:
                if tag.severity in (Severity.CRITICAL, Severity.HIGH):
                    level = _severity_to_gha_level(tag.severity)
                    rec_text = ""
                    if tag.recommendations:
                        rec_text = f" Recommended: {tag.recommendations[0].action}."
                    msg = f"[{tag.framework.value}] {tag.description}{rec_text}"
                    # GitHub limits annotation message to 4096 chars
                    msg = msg[:4090]
                    annotations.append(
                        f"::{level} file={file_result.file_path},"
                        f"line={m.line_start},endLine={m.line_end},"
                        f"title=CRAPQuants: {tag.tag_id}::{msg}"
                    )

    return annotations


def generate_summary(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
    phs_score: float | None = None,
) -> str:
    """
    Generate a GitHub Actions Job Summary in Markdown.

    Written to $GITHUB_STEP_SUMMARY in CI.

    Returns:
        Markdown string for job summary.
    """
    total_functions = sum(len(r.functions) for r in results)
    crappy_count = sum(
        1 for r in results for f in r.functions if f.crap.is_crappy
    )

    lines = [
        "## CRAPQuants Analysis Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Files | {len(results)} |",
        f"| Functions | {total_functions} |",
        f"| CRAPpy (>30) | {crappy_count} |",
    ]
    if phs_score is not None:
        lines.append(f"| Health (PHS) | {phs_score:.0f}/100 |")

    if crappy_count > 0:
        lines.append("")
        lines.append(f"**Result: FAIL** — {crappy_count} function(s) exceed threshold")
    else:
        lines.append("")
        lines.append("**Result: PASS**")

    # Add compact glossary for GitHub summary
    lines.extend([
        "",
        "<details>",
        "<summary>How to read these results</summary>",
        "",
        "**CRAP Score** = CC² × (1 − coverage/100)³ + CC. "
        "Combines complexity with test coverage. Score > 30 = needs attention.",
        "",
        "| Score | Meaning |",
        "|-------|---------|",
        "| 1–10 | Clean — low risk |",
        "| 11–30 | Moderate — consider improving |",
        "| 31–60 | CRAPpy — prioritize for refactoring or testing |",
        "| 61+ | Critical — dangerous to change |",
        "",
        "**CC** = Cyclomatic Complexity (number of paths through code). "
        "**CogC** = Cognitive Complexity (how hard to understand). "
        "**Cov%** = Test coverage percentage.",
        "",
        "Tags like `[Feathers] MONSTER_SNARLED` come from six software engineering books "
        "and identify specific problem patterns with named fixes.",
        "",
        "</details>",
    ])

    return "\n".join(lines)


def print_annotations(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
    crap_threshold: float = 30.0,
    phs_score: float | None = None,
) -> int:
    """
    Print all GitHub Actions annotations and summary to stdout.

    Args:
        results: Merged file results.
        all_tags: Diagnostic tags.
        crap_threshold: CRAP threshold.
        phs_score: PHS score.

    Returns:
        Number of annotations printed.
    """
    annotations = generate_annotations(results, all_tags, crap_threshold)
    for ann in annotations:
        print(ann)

    # Job summary
    summary = generate_summary(results, all_tags, phs_score)
    print(f"\n{summary}")

    return len(annotations)
