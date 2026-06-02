"""
Rich terminal table reporter for CRAPQuants.

Produces human-readable colored terminal output using the `rich` library.
Used in interactive CLI mode (default output format).
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

from crapquants.core.merge import MergedFileResult, MergedFunctionResult
from crapquants.frameworks.tags import DiagnosticTag, Severity


def _severity_color(severity: Severity) -> str:
    """Map severity to rich color."""
    return {
        Severity.INFO: "blue",
        Severity.WARNING: "yellow",
        Severity.HIGH: "red",
        Severity.CRITICAL: "bold red",
    }.get(severity, "white")


def _crap_color(crap_score: float) -> str:
    """Color CRAP score by severity."""
    if crap_score <= 10:
        return "green"
    if crap_score <= 30:
        return "yellow"
    if crap_score <= 60:
        return "red"
    return "bold red"


def _coverage_color(coverage: float) -> str:
    """Color coverage percentage."""
    if coverage >= 80:
        return "green"
    if coverage >= 50:
        return "yellow"
    if coverage >= 20:
        return "red"
    return "bold red"


def render_summary(
    results: list[MergedFileResult],
    phs_score: float | None = None,
    console: Console | None = None,
) -> None:
    """
    Render a summary panel showing codebase-level stats.

    Args:
        results: List of merged file results.
        phs_score: Pragmatic Health Score (0-100) if computed.
        console: Rich console instance (creates new if None).
    """
    console = console or Console()

    total_files = len(results)
    total_functions = sum(len(r.functions) for r in results)
    crappy_count = sum(
        1 for r in results for f in r.functions if f.crap.is_crappy
    )
    total_crap = sum(
        f.crap.crap_score for r in results for f in r.functions
    )
    avg_crap = total_crap / max(total_functions, 1)
    max_crap = max(
        (f.crap.crap_score for r in results for f in r.functions),
        default=0.0,
    )

    summary_text = (
        f"[bold]Files analyzed:[/bold] {total_files}\n"
        f"[bold]Functions analyzed:[/bold] {total_functions}\n"
        f"[bold]Functions above CRAP 30:[/bold] [{_crap_color(crappy_count)}]{crappy_count}[/]\n"
        f"[bold]Average CRAP:[/bold] [{_crap_color(avg_crap)}]{avg_crap:.1f}[/]\n"
        f"[bold]Max CRAP:[/bold] [{_crap_color(max_crap)}]{max_crap:.1f}[/]"
    )

    if phs_score is not None:
        phs_color = "green" if phs_score >= 70 else "yellow" if phs_score >= 40 else "red"
        summary_text += f"\n[bold]Codebase Health (PHS):[/bold] [{phs_color}]{phs_score:.0f}/100[/]"

    console.print(Panel(summary_text, title="CRAPQuants Summary", border_style="cyan"))


def render_function_table(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]] | None = None,
    top_n: int = 20,
    show_passing: bool = False,
    console: Console | None = None,
) -> None:
    """
    Render a table of function-level CRAP scores and diagnostics.

    Args:
        results: List of merged file results.
        all_tags: Optional dict mapping "file:func" to diagnostic tags.
        top_n: Maximum number of functions to display.
        show_passing: If True, show all functions (not just CRAPpy ones).
        console: Rich console instance.
    """
    console = console or Console()

    # Collect all functions, sorted by CRAP score descending
    functions: list[tuple[MergedFunctionResult, str]] = []
    for r in results:
        for f in r.functions:
            functions.append((f, r.file_path))

    functions.sort(key=lambda x: x[0].crap.crap_score, reverse=True)

    if not show_passing:
        functions = [(f, p) for f, p in functions if f.crap.is_crappy]

    if not functions:
        console.print("[green]No CRAPpy functions found. Codebase is clean![/]")
        return

    functions = functions[:top_n]

    table = Table(
        title=f"Top {min(top_n, len(functions))} Functions by CRAP Score",
        show_lines=True,
    )
    table.add_column("Function", style="bold", min_width=25)
    table.add_column("File", style="dim", max_width=35)
    table.add_column("CRAP", justify="right", min_width=6)
    table.add_column("CC", justify="right", min_width=4)
    table.add_column("CogC", justify="right", min_width=5)
    table.add_column("Cov%", justify="right", min_width=5)
    table.add_column("Tags", min_width=30)

    for func, file_path in functions:
        crap = func.crap
        m = func.metrics

        # Build tag string
        tag_key = f"{file_path}:{m.name}"
        tags = all_tags.get(tag_key, []) if all_tags else []
        tag_strs = []
        for t in tags[:4]:  # Show max 4 tags per function
            color = _severity_color(t.severity)
            tag_strs.append(f"[{color}][{t.framework.value}] {t.tag_id}[/]")
        tag_text = "\n".join(tag_strs) if tag_strs else "[dim]—[/]"

        table.add_row(
            m.name,
            _shorten_path(file_path),
            Text(f"{crap.crap_score:.1f}", style=_crap_color(crap.crap_score)),
            str(m.cyclomatic_complexity),
            str(m.cognitive_complexity),
            Text(f"{crap.coverage:.0f}", style=_coverage_color(crap.coverage)),
            tag_text,
        )

    console.print(table)


def render_recommendations(
    all_tags: dict[str, list[DiagnosticTag]],
    top_n: int = 10,
    console: Console | None = None,
) -> None:
    """
    Render actionable refactoring recommendations from all tags.

    Args:
        all_tags: Dict mapping "file:func" to diagnostic tags.
        top_n: Maximum number of recommendations to show.
        console: Rich console instance.
    """
    console = console or Console()

    # Collect all recommendations with context
    recs: list[tuple[str, str, DiagnosticTag]] = []
    for key, tags in all_tags.items():
        for tag in tags:
            if tag.recommendations:
                recs.append((key, tag.recommendations[0].action, tag))

    if not recs:
        return

    # Deduplicate by action + tag_id, keep highest severity
    seen: set[str] = set()
    unique_recs: list[tuple[str, str, DiagnosticTag]] = []
    for key, action, tag in recs:
        dedup_key = f"{key}:{tag.tag_id}"
        if dedup_key not in seen:
            seen.add(dedup_key)
            unique_recs.append((key, action, tag))

    # Sort by severity (critical first)
    severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.WARNING: 2, Severity.INFO: 3}
    unique_recs.sort(key=lambda x: severity_order.get(x[2].severity, 4))
    unique_recs = unique_recs[:top_n]

    table = Table(title="Recommended Actions", show_lines=True)
    table.add_column("Priority", justify="center", min_width=4)
    table.add_column("Function", style="bold", min_width=20)
    table.add_column("Action", min_width=25)
    table.add_column("From", min_width=10)
    table.add_column("Rationale", min_width=30)

    for i, (key, action, tag) in enumerate(unique_recs, 1):
        func_name = key.split(":")[-1] if ":" in key else key
        color = _severity_color(tag.severity)
        table.add_row(
            f"[{color}]{i}[/]",
            func_name,
            action,
            f"[{color}][{tag.framework.value}] {tag.tag_id}[/]",
            tag.recommendations[0].rationale if tag.recommendations else "",
        )

    console.print(table)


def render_full_report(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
    phs_score: float | None = None,
    top_n: int = 20,
    show_passing: bool = False,
    console: Console | None = None,
) -> None:
    """
    Render the complete CRAPQuants terminal report.

    Args:
        results: List of merged file results.
        all_tags: Dict mapping "file:func" to diagnostic tags.
        phs_score: Pragmatic Health Score.
        top_n: Maximum functions to show.
        show_passing: Show all functions or only CRAPpy ones.
        console: Rich console instance.
    """
    console = console or Console()

    console.print()
    console.rule("[bold cyan]CRAPQuants Report[/]")
    console.print()

    render_summary(results, phs_score, console)
    console.print()
    render_function_table(results, all_tags, top_n, show_passing, console)
    console.print()
    render_recommendations(all_tags, top_n=10, console=console)
    console.print()
    _render_glossary(console)
    console.print()


def _render_glossary(console: Console) -> None:
    """Render the How to Read This Report glossary panel."""
    from crapquants.reporting.glossary import (
        CRAP_EXPLANATION, CRAP_THRESHOLDS,
        CC_EXPLANATION, CC_THRESHOLDS,
        COGC_EXPLANATION, COGC_THRESHOLDS,
        COVERAGE_EXPLANATION, COVERAGE_THRESHOLDS,
        PHS_EXPLANATION, PHS_THRESHOLDS,
        SEVERITY_EXPLANATION, WHAT_TO_DO_NEXT,
    )

    glossary_text = (
        "[bold underline]What is CRAP?[/]\n"
        f"{CRAP_EXPLANATION}\n\n"
        f"[dim]{CRAP_THRESHOLDS}[/]\n\n"
        "[bold underline]Column Definitions[/]\n"
        f"[bold]CC:[/] {CC_EXPLANATION}\n"
        f"[dim]{CC_THRESHOLDS}[/]\n\n"
        f"[bold]CogC:[/] {COGC_EXPLANATION}\n"
        f"[dim]{COGC_THRESHOLDS}[/]\n\n"
        f"[bold]Cov%:[/] {COVERAGE_EXPLANATION}\n"
        f"[dim]{COVERAGE_THRESHOLDS}[/]\n\n"
        "[bold underline]Codebase Health (PHS)[/]\n"
        f"{PHS_EXPLANATION}\n"
        f"[dim]{PHS_THRESHOLDS}[/]\n\n"
        "[bold underline]Tag Severity[/]\n"
        f"{SEVERITY_EXPLANATION}\n\n"
        "[bold underline]What To Do Next[/]\n"
        f"{WHAT_TO_DO_NEXT}"
    )

    console.print(Panel(
        glossary_text,
        title="How to Read This Report",
        border_style="dim cyan",
        padding=(1, 2),
    ))


def _shorten_path(path: str, max_len: int = 35) -> str:
    """Shorten a file path for display."""
    if len(path) <= max_len:
        return path
    parts = path.split("/")
    if len(parts) <= 2:
        return f"...{path[-(max_len - 3):]}"
    return f".../{'/'.join(parts[-2:])}"
