"""
Shared glossary and explanation text for CRAPQuants reports.

Every report format (table, JSON, Markdown, SARIF, GHA) uses this module
to produce self-documenting output that a first-time reader can understand
without external documentation.

Design principle: If someone reads a CRAPQuants report for the first time
and has to Google what "CRAP" means, the report has failed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Score explanations with thresholds
# ---------------------------------------------------------------------------

CRAP_EXPLANATION = (
    "CRAP (Change Risk Anti-Patterns) measures how risky a function is to change. "
    "It combines cyclomatic complexity (how many paths through the code) with "
    "test coverage (how many of those paths are tested).\n"
    "Formula: CRAP = CC² × (1 − coverage/100)³ + CC\n"
    "A high-complexity function with good test coverage can still be safe. "
    "A simple function with no tests is risky. CRAP captures this tradeoff."
)

CRAP_THRESHOLDS = (
    "CRAP Score Interpretation:\n"
    "  1–10   : Clean — low risk, easy to change safely\n"
    "  11–30  : Moderate — manageable, but consider adding tests or simplifying\n"
    "  31–60  : CRAPpy — high risk, prioritize for refactoring or testing\n"
    "  61+    : Critical — very high risk, changes here are dangerous"
)

CC_EXPLANATION = (
    "CC (Cyclomatic Complexity) counts the number of independent paths through a function. "
    "Each if, for, while, except, and boolean operator adds a path. "
    "CC=1 means straight-line code with no branching. "
    "CC=10+ means the function has many branches and is hard to test completely."
)

CC_THRESHOLDS = (
    "CC Score Interpretation:\n"
    "  1–5    : Simple — easy to understand and test\n"
    "  6–10   : Moderate — consider splitting if growing\n"
    "  11–20  : Complex — hard to test, should be refactored\n"
    "  21–30  : Very complex — refactoring strongly recommended\n"
    "  31+    : Untestable — no amount of testing makes this safe, must simplify"
)

COGC_EXPLANATION = (
    "CogC (Cognitive Complexity) measures how hard a function is to understand "
    "by a human reading it. Unlike CC, it penalizes deeply nested code more heavily. "
    "A flat switch statement (CC=10) is easier to read than 4 nested if-for-while loops (CC=4), "
    "and CogC reflects this."
)

COGC_THRESHOLDS = (
    "CogC Score Interpretation:\n"
    "  0–5    : Easy to understand at a glance\n"
    "  6–15   : Requires careful reading\n"
    "  16–25  : Difficult — consider breaking up\n"
    "  25+    : Very difficult — likely understood by only 1-2 developers"
)

COVERAGE_EXPLANATION = (
    "Cov% (Code Coverage) shows what percentage of a function's lines are "
    "executed by automated tests. Higher coverage means more confidence that "
    "changes won't break things silently. 0% means no tests exist for this function."
)

COVERAGE_THRESHOLDS = (
    "Coverage Interpretation:\n"
    "  80–100%: Well tested — safe to refactor with confidence\n"
    "  50–79% : Partially tested — some risk when changing\n"
    "  20–49% : Weakly tested — significant risk of undetected bugs\n"
    "  0–19%  : Untested — any change is 'Edit and Pray'"
)

PHS_EXPLANATION = (
    "PHS (Pragmatic Health Score) rates overall codebase quality on a 0–100 scale. "
    "It penalizes CRAPpy functions, broken windows (neglected bad code), "
    "coincidence programming (code that works but nobody knows why), "
    "and functions with no test safety net."
)

PHS_THRESHOLDS = (
    "PHS Interpretation:\n"
    "  80–100 : Healthy — well-maintained, sustainable pace\n"
    "  60–79  : Moderate — some tech debt accumulating\n"
    "  40–59  : Unhealthy — significant quality issues\n"
    "  0–39   : Critical — codebase is actively degrading"
)

CRAPLOAD_EXPLANATION = (
    "CRAPload estimates the minimum work needed to bring a function below the CRAP threshold: "
    "how many tests to write (for uncovered paths) plus how many refactorings "
    "(for complexity that tests alone can't fix)."
)

# ---------------------------------------------------------------------------
# Tag framework explanations
# ---------------------------------------------------------------------------

FRAMEWORK_EXPLANATIONS = {
    "Feathers": (
        "Feathers tags (from 'Working Effectively with Legacy Code' by Michael Feathers) "
        "identify testability barriers — why a function is hard to get under test, "
        "and which dependency-breaking techniques to apply first."
    ),
    "Ousterhout": (
        "Ousterhout tags (from 'A Philosophy of Software Design' by John Ousterhout) "
        "identify design quality issues — shallow modules, vague naming, nonobvious code, "
        "and interface complexity that makes code harder to work with."
    ),
    "Hunt & Thomas": (
        "Hunt & Thomas tags (from 'The Pragmatic Programmer' by Andrew Hunt & David Thomas) "
        "identify engineering culture issues — broken windows, programming by coincidence, "
        "and missing safety nets that degrade codebase quality over time."
    ),
    "Fowler": (
        "Fowler tags (from 'Refactoring' by Martin Fowler & Kent Beck) "
        "identify specific code smells and prescribe named refactoring transformations. "
        "Each recommendation is a well-defined, repeatable technique."
    ),
    "Tornhill": (
        "Tornhill tags (from 'Your Code as a Crime Scene' by Adam Tornhill) "
        "identify behavioral risk — hotspots that change frequently, knowledge silos "
        "where only one developer understands the code, and complexity trends."
    ),
    "Ford": (
        "Ford tags (from 'Building Evolutionary Architectures' by Neal Ford et al.) "
        "enforce architectural fitness functions — automated quality gates that prevent "
        "the codebase from drifting away from its intended design."
    ),
}

# ---------------------------------------------------------------------------
# Severity explanations
# ---------------------------------------------------------------------------

SEVERITY_EXPLANATION = (
    "Tag Severity Levels:\n"
    "  🔴 CRITICAL : Immediate action required — high risk of production issues\n"
    "  🟠 HIGH     : Should fix soon — significant maintenance or reliability risk\n"
    "  🟡 WARNING  : Worth addressing — will cause problems if ignored long-term\n"
    "  🔵 INFO     : Informational — positive signals or minor suggestions"
)

# ---------------------------------------------------------------------------
# What To Do Next section
# ---------------------------------------------------------------------------

WHAT_TO_DO_NEXT = (
    "What To Do Next:\n"
    "1. Start with CRITICAL and HIGH severity items — these are your highest-risk functions\n"
    "2. For each flagged function, read the 'Recommended Action' — it tells you the specific\n"
    "   refactoring technique to apply (e.g., 'Extract Method', 'Decompose Conditional')\n"
    "3. Write tests BEFORE refactoring — the Feathers approach: cover first, then change\n"
    "4. Tackle one function at a time — small improvements compound over time\n"
    "5. Re-run CRAPQuants after each change to verify improvement"
)

# ---------------------------------------------------------------------------
# Combined glossary for report footer
# ---------------------------------------------------------------------------

def build_glossary_markdown() -> str:
    """Build a complete Markdown glossary section for reports."""
    lines = [
        "## How to Read This Report",
        "",
        "### What is CRAP?",
        CRAP_EXPLANATION,
        "",
        "```",
        CRAP_THRESHOLDS,
        "```",
        "",
        "### Column Definitions",
        "",
        f"**CC (Cyclomatic Complexity):** {CC_EXPLANATION}",
        "",
        "```",
        CC_THRESHOLDS,
        "```",
        "",
        f"**CogC (Cognitive Complexity):** {COGC_EXPLANATION}",
        "",
        "```",
        COGC_THRESHOLDS,
        "```",
        "",
        f"**Cov% (Coverage):** {COVERAGE_EXPLANATION}",
        "",
        "```",
        COVERAGE_THRESHOLDS,
        "```",
        "",
        f"**CRAPload:** {CRAPLOAD_EXPLANATION}",
        "",
        "### Codebase Health (PHS)",
        PHS_EXPLANATION,
        "",
        "```",
        PHS_THRESHOLDS,
        "```",
        "",
        "### Diagnostic Tags",
        "Tags are diagnostic findings from six software engineering books. "
        "Each tag identifies a specific problem pattern and recommends a named fix.",
        "",
        SEVERITY_EXPLANATION,
        "",
        "**Tag Sources:**",
        "",
    ]
    for framework, explanation in FRAMEWORK_EXPLANATIONS.items():
        lines.append(f"- **[{framework}]** — {explanation}")
    lines.append("")
    lines.append(f"### {WHAT_TO_DO_NEXT}")
    lines.append("")

    return "\n".join(lines)


def build_glossary_plaintext() -> str:
    """Build a plaintext glossary for terminal/table output."""
    sections = [
        "═══ HOW TO READ THIS REPORT ═══",
        "",
        "WHAT IS CRAP?",
        CRAP_EXPLANATION,
        "",
        CRAP_THRESHOLDS,
        "",
        "COLUMN DEFINITIONS",
        f"CC:   {CC_EXPLANATION}",
        CC_THRESHOLDS,
        "",
        f"CogC: {COGC_EXPLANATION}",
        COGC_THRESHOLDS,
        "",
        f"Cov%: {COVERAGE_EXPLANATION}",
        COVERAGE_THRESHOLDS,
        "",
        f"CRAPload: {CRAPLOAD_EXPLANATION}",
        "",
        "CODEBASE HEALTH (PHS)",
        PHS_EXPLANATION,
        PHS_THRESHOLDS,
        "",
        "TAG SEVERITY",
        SEVERITY_EXPLANATION,
        "",
        WHAT_TO_DO_NEXT,
    ]
    return "\n".join(sections)


def build_glossary_json() -> dict:
    """Build a glossary dict for JSON report inclusion."""
    return {
        "crap_score": {
            "description": CRAP_EXPLANATION,
            "thresholds": {
                "clean": "1–10",
                "moderate": "11–30",
                "crappy": "31–60",
                "critical": "61+",
            },
            "formula": "CC² × (1 − coverage/100)³ + CC",
            "threshold": 30,
        },
        "cyclomatic_complexity": {
            "description": CC_EXPLANATION,
            "thresholds": {
                "simple": "1–5",
                "moderate": "6–10",
                "complex": "11–20",
                "very_complex": "21–30",
                "untestable": "31+",
            },
        },
        "cognitive_complexity": {
            "description": COGC_EXPLANATION,
            "thresholds": {
                "easy": "0–5",
                "careful_reading": "6–15",
                "difficult": "16–25",
                "very_difficult": "25+",
            },
        },
        "coverage_percent": {
            "description": COVERAGE_EXPLANATION,
            "thresholds": {
                "well_tested": "80–100%",
                "partial": "50–79%",
                "weak": "20–49%",
                "untested": "0–19%",
            },
        },
        "crapload": {"description": CRAPLOAD_EXPLANATION},
        "pragmatic_health_score": {
            "description": PHS_EXPLANATION,
            "thresholds": {
                "healthy": "80–100",
                "moderate": "60–79",
                "unhealthy": "40–59",
                "critical": "0–39",
            },
        },
        "severity_levels": {
            "critical": "Immediate action required",
            "high": "Should fix soon",
            "warning": "Worth addressing",
            "info": "Informational or positive signal",
        },
        "frameworks": FRAMEWORK_EXPLANATIONS,
        "what_to_do_next": WHAT_TO_DO_NEXT,
    }
