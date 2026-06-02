"""
CRAPQuants CLI — Interactive command-line interface.

Entry point: `crapquants analyze`

Wires together:
    - core/ (metrics computation)
    - frameworks/ (diagnostic tags from 6 books)
    - reporting/ (5 output formats)

Usage:
    crapquants analyze --path ./src --coverage coverage.json
    crapquants analyze --path ./src --format json --output report.json
    crapquants analyze --path ./src --level deep
"""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from crapquants.core.complexity import analyze_file
from crapquants.core.coverage_parser import (
    FileCoverage,
    parse_coverage_json,
    parse_coverage_lcov,
)
from crapquants.core.merge import MergedFileResult, merge_file
from crapquants.frameworks import feathers, ousterhout, hunt_thomas, fowler, tornhill, ford
from crapquants.frameworks.tags import DiagnosticTag
from crapquants.frameworks.hunt_thomas import CodebaseHealth, compute_pragmatic_health_score
from crapquants.reporting.table import render_full_report
from crapquants.reporting.json_report import write_json_report
from crapquants.reporting.markdown_report import write_markdown_report
from crapquants.reporting.sarif import write_sarif_report
from crapquants.reporting.github_actions import print_annotations

app = typer.Typer(
    name="crapquants",
    help="CRAPQuants — Python-native CRAP metric tool with book-integrated diagnostics.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# Enums for CLI options
# ---------------------------------------------------------------------------

class AnalysisLevel(str, Enum):
    quick = "quick"
    standard = "standard"
    deep = "deep"
    full = "full"


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    markdown = "markdown"
    sarif = "sarif"
    github_actions = "github_actions"


class MissingPolicy(str, Enum):
    pessimistic = "pessimistic"
    optimistic = "optimistic"
    skip = "skip"


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def discover_python_files(path: Path, exclude_patterns: list[str] | None = None) -> list[Path]:
    """
    Discover Python files to analyze.

    Args:
        path: Directory or single file path.
        exclude_patterns: Glob patterns to exclude (e.g., ["test_*", "__pycache__"]).

    Returns:
        Sorted list of .py file paths.
    """
    exclude_patterns = exclude_patterns or ["test_*", "conftest.py", "__pycache__"]

    if path.is_file():
        if path.suffix == ".py":
            return [path]
        return []

    files: list[Path] = []
    for py_file in sorted(path.rglob("*.py")):
        # Skip excluded patterns
        skip = False
        for pattern in exclude_patterns:
            if py_file.match(pattern):
                skip = True
                break
        # Skip __pycache__ directories
        if "__pycache__" in str(py_file):
            skip = True
        if not skip:
            files.append(py_file)

    return files


# ---------------------------------------------------------------------------
# Coverage loading
# ---------------------------------------------------------------------------

def load_coverage(coverage_path: Path | None, coverage_format: str) -> list[FileCoverage]:
    """Load coverage data from file."""
    if coverage_path is None or not coverage_path.exists():
        return []

    if coverage_format == "json" or coverage_path.suffix == ".json":
        return parse_coverage_json(coverage_path)
    elif coverage_format == "lcov" or coverage_path.suffix in (".lcov", ".info"):
        return parse_coverage_lcov(coverage_path)
    else:
        # Try JSON first, then LCOV
        try:
            return parse_coverage_json(coverage_path)
        except (ValueError, KeyError):
            return parse_coverage_lcov(coverage_path)


# ---------------------------------------------------------------------------
# Framework runner
# ---------------------------------------------------------------------------

def run_frameworks(
    merged: MergedFileResult,
    level: AnalysisLevel,
) -> dict[str, list[DiagnosticTag]]:
    """
    Run diagnostic frameworks on all functions in a merged file result.

    Args:
        merged: Merged file result.
        level: Analysis level (quick skips frameworks).

    Returns:
        Dict mapping "file:func_name" to list of diagnostic tags.
    """
    tags: dict[str, list[DiagnosticTag]] = {}

    if level == AnalysisLevel.quick:
        # Quick mode: only CRAP scores, no framework tags
        # Still run Ford fitness functions (they're threshold-based, fast)
        for func in merged.functions:
            key = f"{merged.file_path}:{func.metrics.name}"
            func_tags = ford.analyze(func)
            if func_tags:
                tags[key] = func_tags
        return tags

    # Standard / Deep / Full: run all 6 frameworks
    for func in merged.functions:
        key = f"{merged.file_path}:{func.metrics.name}"
        func_tags: list[DiagnosticTag] = []
        func_tags.extend(feathers.analyze(func))
        func_tags.extend(ousterhout.analyze(func))
        func_tags.extend(hunt_thomas.analyze(func))
        func_tags.extend(fowler.analyze(func))
        func_tags.extend(tornhill.analyze(func))
        func_tags.extend(ford.analyze(func))
        if func_tags:
            tags[key] = func_tags

    return tags


# ---------------------------------------------------------------------------
# PHS computation
# ---------------------------------------------------------------------------

def compute_phs(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
) -> float:
    """Compute Pragmatic Health Score from results and tags."""
    total = sum(len(r.functions) for r in results)
    crappy = sum(1 for r in results for f in r.functions if f.crap.is_crappy)
    bw = sum(1 for tags in all_tags.values() for t in tags if t.tag_id == "BROKEN_WINDOW")
    coinc = sum(1 for tags in all_tags.values() for t in tags if t.tag_id == "COINCIDENCE_CODE")
    nsn = sum(1 for tags in all_tags.values() for t in tags if t.tag_id == "NO_SAFETY_NET")

    health = CodebaseHealth(
        total_functions=total,
        crappy_functions=crappy,
        broken_window_count=bw,
        coincidence_count=coinc,
        no_safety_net_count=nsn,
    )
    return compute_pragmatic_health_score(health)


# ---------------------------------------------------------------------------
# Main CLI command
# ---------------------------------------------------------------------------

@app.command()
def analyze(
    path: Path = typer.Argument(
        ...,
        help="Path to Python file or directory to analyze.",
        exists=True,
    ),
    coverage: Optional[Path] = typer.Option(
        None, "--coverage", "-c",
        help="Path to coverage report (JSON or LCOV). If omitted, 0%% coverage assumed.",
    ),
    coverage_format: str = typer.Option(
        "auto", "--coverage-format",
        help="Coverage file format: json, lcov, or auto (detect from extension).",
    ),
    level: AnalysisLevel = typer.Option(
        AnalysisLevel.standard, "--level", "-l",
        help="Analysis depth: quick (CRAP only), standard (+ frameworks), deep (+ git), full (+ mutation + SAST).",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f",
        help="Output format: table, json, markdown, sarif, github_actions.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output file path. If omitted, prints to stdout (table/github_actions) or uses default name.",
    ),
    threshold: float = typer.Option(
        30.0, "--threshold", "-t",
        help="CRAP score threshold. Functions above this are flagged.",
    ),
    top_n: int = typer.Option(
        20, "--top-n",
        help="Maximum number of functions to show in report.",
    ),
    show_passing: bool = typer.Option(
        False, "--show-passing",
        help="Include functions below CRAP threshold in report.",
    ),
    missing_policy: MissingPolicy = typer.Option(
        MissingPolicy.pessimistic, "--missing-policy",
        help="How to handle functions without coverage: pessimistic (0%%), optimistic (100%%), skip.",
    ),
    exclude: Optional[list[str]] = typer.Option(
        None, "--exclude", "-e",
        help="Glob patterns to exclude (e.g., 'test_*'). Can be repeated.",
    ),
    baseline: Optional[Path] = typer.Option(
        None, "--baseline", "-b",
        help="Path to baseline JSON for regression detection. Compares current vs saved.",
    ),
    save_baseline_path: Optional[Path] = typer.Option(
        None, "--save-baseline",
        help="Save current scores as baseline to this path (e.g., data/baseline.json).",
    ),
) -> None:
    """
    Analyze Python code for CRAP scores and diagnostic tags.

    Computes CRAP (Change Risk Anti-Patterns) scores by combining
    cyclomatic complexity with test coverage. Enriches results with
    diagnostic tags from six software engineering books.

    Examples:
        crapquants analyze ./src
        crapquants analyze ./src -c coverage.json -f markdown -o report.md
        crapquants analyze ./src -l quick -t 20
        crapquants analyze myfile.py -c coverage.lcov --show-passing
    """
    # Suppress noisy structlog output in CLI mode
    import logging
    import structlog
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
    )

    # Step 1: Discover files
    exclude_patterns = list(exclude) if exclude else ["test_*", "conftest.py"]
    py_files = discover_python_files(path, exclude_patterns)

    if not py_files:
        console.print(f"[red]No Python files found in {path}[/]")
        raise typer.Exit(code=1)

    # Step 2: Load coverage
    coverage_data = load_coverage(coverage, coverage_format)
    cov_status = f"{len(coverage_data)} files" if coverage_data else "none (0% assumed)"

    if format == OutputFormat.table:
        console.print()
        console.print(f"[bold cyan]CRAPQuants v1.0.0[/] — Code Quality Analysis")
        console.print(f"  Path: [bold]{path}[/]")
        console.print(f"  Level: [bold]{level.value}[/]")
        console.print(f"  Coverage: {cov_status}")
        console.print(f"  Files: [bold]{len(py_files)}[/] Python files")
        console.print()

    # Step 3: Analyze files
    merged_results: list[MergedFileResult] = []
    all_tags: dict[str, list[DiagnosticTag]] = {}
    errors: list[str] = []

    if format == OutputFormat.table:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing...", total=len(py_files))
            for py_file in py_files:
                try:
                    file_metrics = analyze_file(py_file)
                    merged = merge_file(
                        file_metrics,
                        coverage_data,
                        crap_threshold=threshold,
                        missing_policy=missing_policy.value,
                    )
                    merged_results.append(merged)

                    # Run frameworks
                    file_tags = run_frameworks(merged, level)
                    all_tags.update(file_tags)

                except SyntaxError as e:
                    errors.append(f"Syntax error in {py_file}: {e}")
                except Exception as e:
                    errors.append(f"Error analyzing {py_file}: {e}")

                progress.advance(task)
    else:
        # Non-interactive mode (JSON, MD, SARIF, GHA)
        for py_file in py_files:
            try:
                file_metrics = analyze_file(py_file)
                merged = merge_file(
                    file_metrics,
                    coverage_data,
                    crap_threshold=threshold,
                    missing_policy=missing_policy.value,
                )
                merged_results.append(merged)
                file_tags = run_frameworks(merged, level)
                all_tags.update(file_tags)
            except SyntaxError as e:
                errors.append(f"Syntax error in {py_file}: {e}")
            except Exception as e:
                errors.append(f"Error analyzing {py_file}: {e}")

    if not merged_results:
        console.print("[red]No files could be analyzed successfully.[/]")
        if errors:
            for err in errors:
                console.print(f"  [dim red]{err}[/]")
        raise typer.Exit(code=1)

    # Step 4: Compute PHS
    phs = compute_phs(merged_results, all_tags)

    # Step 5: Output
    crappy_count = sum(
        1 for r in merged_results for f in r.functions if f.crap.is_crappy
    )

    if format == OutputFormat.table:
        if errors:
            console.print(f"[dim yellow]Skipped {len(errors)} file(s) with errors[/]")
        render_full_report(
            merged_results, all_tags,
            phs_score=phs, top_n=top_n,
            show_passing=show_passing, console=console,
        )

    elif format == OutputFormat.json:
        output_path = str(output) if output else "crapquants_report.json"
        write_json_report(
            merged_results, all_tags, output_path,
            phs_score=phs, analysis_level=level.value,
        )
        if output:
            console.print(f"Report written to {output_path}")

    elif format == OutputFormat.markdown:
        output_path = str(output) if output else "crapquants_report.md"
        write_markdown_report(
            merged_results, all_tags, output_path,
            phs_score=phs, analysis_level=level.value, top_n=top_n,
        )
        if output:
            console.print(f"Report written to {output_path}")

    elif format == OutputFormat.sarif:
        output_path = str(output) if output else "crapquants_report.sarif"
        write_sarif_report(merged_results, all_tags, output_path)
        if output:
            console.print(f"Report written to {output_path}")

    elif format == OutputFormat.github_actions:
        print_annotations(
            merged_results, all_tags,
            crap_threshold=threshold, phs_score=phs,
        )

    # Step 6: Baseline save/compare
    if save_baseline_path:
        from crapquants.baseline.save import save_baseline as do_save_baseline
        saved = do_save_baseline(merged_results, save_baseline_path)
        console.print(f"[green]Baseline saved to {saved}[/]")

    if baseline:
        from crapquants.baseline.compare import compare as do_compare
        try:
            comp = do_compare(merged_results, baseline, crap_threshold=threshold)
            if format == OutputFormat.table:
                console.print()
                if comp.is_regression:
                    console.print(f"[bold red]Baseline comparison: REGRESSION[/]")
                else:
                    console.print(f"[bold green]Baseline comparison: OK[/]")
                console.print(f"  Aggregate CRAP delta: {comp.aggregate_delta:+.1f}")
                if comp.new_crappy:
                    console.print(f"  [red]New CRAPpy: {len(comp.new_crappy)}[/]")
                    for fd in comp.new_crappy[:5]:
                        console.print(f"    {fd.function} ({fd.file}): {fd.baseline_crap:.1f} → {fd.current_crap:.1f}")
                if comp.fixed:
                    console.print(f"  [green]Fixed: {len(comp.fixed)}[/]")
                if comp.worsened:
                    console.print(f"  [yellow]Worsened: {len(comp.worsened)}[/]")
                if comp.improved:
                    console.print(f"  [green]Improved: {len(comp.improved)}[/]")
                console.print()

            if comp.is_regression:
                crappy_count = max(crappy_count, 1)  # Force exit code 1 on regression
        except FileNotFoundError:
            console.print(f"[yellow]Baseline not found: {baseline}. Skipping comparison.[/]")

    # Exit code: non-zero if CRAPpy functions found (for CI gates)
    if crappy_count > 0:
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Show CRAPQuants version."""
    from crapquants import __version__
    console.print(f"CRAPQuants v{__version__}")


if __name__ == "__main__":
    app()
