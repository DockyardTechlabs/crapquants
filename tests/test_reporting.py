"""Tests for CRAPQuants reporting modules."""

import json
from io import StringIO

import pytest
from rich.console import Console

from crapquants.core.complexity import FunctionMetrics
from crapquants.core.crap import CRAPResult, calculate_crap
from crapquants.core.coverage_parser import FileCoverage
from crapquants.core.merge import MergedFileResult, MergedFunctionResult
from crapquants.frameworks.tags import (
    DiagnosticTag,
    Framework,
    Recommendation,
    Severity,
)
from crapquants.reporting.table import render_summary, render_function_table, render_full_report
from crapquants.reporting.json_report import generate_json_report, write_json_report
from crapquants.reporting.markdown_report import generate_markdown_report, write_markdown_report
from crapquants.reporting.sarif import generate_sarif_report, write_sarif_report
from crapquants.reporting.github_actions import generate_annotations, generate_summary


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_func(name="func", cc=5, cov=50.0, cogc=5, lines=20, params=2,
               abc_a=3, abc_b=5, abc_c=3, abc_s=7.0):
    crap_score = calculate_crap(cc, cov)
    return MergedFunctionResult(
        metrics=FunctionMetrics(
            name=name, file_path="src/module.py", line_start=1, line_end=lines,
            cyclomatic_complexity=cc, cognitive_complexity=cogc,
            abc_assignments=abc_a, abc_branches=abc_b, abc_conditions=abc_c,
            abc_scalar=abc_s, line_count=lines,
            max_nesting_depth=2, parameter_count=params,
        ),
        coverage=None,
        crap=CRAPResult(
            function_name=name, file_path="src/module.py", line_number=1,
            complexity=cc, coverage=cov, crap_score=crap_score,
            crapload=0, is_crappy=crap_score > 30,
            min_coverage_needed=0.0, complexity_threshold_exceeded=cc >= 31,
        ),
    )


def _make_file_result(functions=None):
    if functions is None:
        functions = [
            _make_func("clean_func", cc=3, cov=100.0),
            _make_func("crappy_func", cc=15, cov=0.0),
        ]
    return MergedFileResult(
        file_path="src/module.py",
        file_metrics=type('FM', (), {
            'halstead_volume': 100.0, 'halstead_difficulty': 5.0,
            'halstead_effort': 500.0, 'maintainability_index': 65.0,
            'total_lines': 50, 'code_lines': 40,
            'comment_lines': 5, 'blank_lines': 5,
        })(),
        file_coverage=None,
        functions=functions,
    )


def _make_tags():
    return {
        "src/module.py:crappy_func": [
            DiagnosticTag(
                tag_id="MONSTER_SNARLED",
                framework=Framework.FEATHERS,
                severity=Severity.HIGH,
                description="Snarled monster method: CC=15, nesting=5.",
                recommendations=(
                    Recommendation("Extract Method", "Split by responsibility", 1),
                ),
            ),
            DiagnosticTag(
                tag_id="EDIT_AND_PRAY",
                framework=Framework.FEATHERS,
                severity=Severity.HIGH,
                description="No coverage with CC=15.",
                recommendations=(
                    Recommendation("Write Characterization Tests", "Document behavior", 1),
                ),
            ),
        ],
    }


@pytest.fixture
def sample_results():
    return [_make_file_result()]


@pytest.fixture
def sample_tags():
    return _make_tags()


# ---------------------------------------------------------------------------
# Table reporter tests
# ---------------------------------------------------------------------------

class TestTableReporter:
    def test_render_summary_no_error(self, sample_results):
        console = Console(file=StringIO(), force_terminal=True, width=120)
        render_summary(sample_results, phs_score=72.0, console=console)
        output = console.file.getvalue()
        assert "CRAPQuants" in output

    def test_render_function_table_no_error(self, sample_results, sample_tags):
        console = Console(file=StringIO(), force_terminal=True, width=120)
        render_function_table(sample_results, sample_tags, console=console)
        output = console.file.getvalue()
        assert "crappy_func" in output

    def test_render_function_table_empty_clean(self):
        results = [_make_file_result([_make_func("good", cc=2, cov=100.0)])]
        console = Console(file=StringIO(), force_terminal=True, width=120)
        render_function_table(results, {}, console=console)
        output = console.file.getvalue()
        assert "clean" in output.lower()

    def test_render_full_report_no_error(self, sample_results, sample_tags):
        console = Console(file=StringIO(), force_terminal=True, width=120)
        render_full_report(sample_results, sample_tags, phs_score=65.0, console=console)
        output = console.file.getvalue()
        assert len(output) > 100


# ---------------------------------------------------------------------------
# JSON reporter tests
# ---------------------------------------------------------------------------

class TestJsonReporter:
    def test_generates_valid_json(self, sample_results, sample_tags):
        report = generate_json_report(sample_results, sample_tags)
        # Validate it serializes
        json_str = json.dumps(report)
        assert len(json_str) > 100

    def test_schema_version_present(self, sample_results, sample_tags):
        report = generate_json_report(sample_results, sample_tags)
        assert report["schema_version"] == "1.0.0"

    def test_summary_fields(self, sample_results, sample_tags):
        report = generate_json_report(sample_results, sample_tags)
        summary = report["summary"]
        assert summary["files_analyzed"] == 1
        assert summary["functions_analyzed"] == 2
        assert summary["crappy_functions"] == 1

    def test_function_tags_included(self, sample_results, sample_tags):
        report = generate_json_report(sample_results, sample_tags)
        funcs = report["files"][0]["functions"]
        crappy = [f for f in funcs if f["name"] == "crappy_func"][0]
        assert len(crappy["tags"]) == 2
        assert crappy["tags"][0]["tag_id"] == "MONSTER_SNARLED"

    def test_write_to_file(self, sample_results, sample_tags, tmp_path):
        path = str(tmp_path / "report.json")
        write_json_report(sample_results, sample_tags, path)
        with open(path) as f:
            data = json.load(f)
        assert data["tool"] == "crapquants"

    def test_phs_included(self, sample_results, sample_tags):
        report = generate_json_report(sample_results, sample_tags, phs_score=72.0)
        assert report["summary"]["pragmatic_health_score"] == 72.0


# ---------------------------------------------------------------------------
# Markdown reporter tests
# ---------------------------------------------------------------------------

class TestMarkdownReporter:
    def test_generates_markdown(self, sample_results, sample_tags):
        md = generate_markdown_report(sample_results, sample_tags)
        assert "# CRAPQuants Report" in md
        assert "crappy_func" in md

    def test_gate_fail_message(self, sample_results, sample_tags):
        md = generate_markdown_report(sample_results, sample_tags)
        assert "FAIL" in md

    def test_gate_pass_message(self):
        results = [_make_file_result([_make_func("good", cc=2, cov=100.0)])]
        md = generate_markdown_report(results, {})
        assert "PASS" in md

    def test_phs_included(self, sample_results, sample_tags):
        md = generate_markdown_report(sample_results, sample_tags, phs_score=85.0)
        assert "85" in md

    def test_recommendations_included(self, sample_results, sample_tags):
        md = generate_markdown_report(sample_results, sample_tags)
        assert "Extract Method" in md

    def test_write_to_file(self, sample_results, sample_tags, tmp_path):
        path = str(tmp_path / "report.md")
        write_markdown_report(sample_results, sample_tags, path)
        with open(path) as f:
            content = f.read()
        assert "CRAPQuants" in content


# ---------------------------------------------------------------------------
# SARIF reporter tests
# ---------------------------------------------------------------------------

class TestSarifReporter:
    def test_valid_sarif_structure(self, sample_results, sample_tags):
        sarif = generate_sarif_report(sample_results, sample_tags)
        assert sarif["version"] == "2.1.0"
        assert "$schema" in sarif
        assert len(sarif["runs"]) == 1

    def test_tool_info(self, sample_results, sample_tags):
        sarif = generate_sarif_report(sample_results, sample_tags)
        tool = sarif["runs"][0]["tool"]["driver"]
        assert tool["name"] == "CRAPQuants"
        assert tool["version"] == "1.0.0"

    def test_results_contain_crap_violations(self, sample_results, sample_tags):
        sarif = generate_sarif_report(sample_results, sample_tags)
        results = sarif["runs"][0]["results"]
        crap_results = [r for r in results if r["ruleId"] == "crapquants/crap-threshold"]
        assert len(crap_results) == 1  # Only crappy_func

    def test_results_contain_tag_violations(self, sample_results, sample_tags):
        sarif = generate_sarif_report(sample_results, sample_tags)
        results = sarif["runs"][0]["results"]
        tag_results = [r for r in results if "feathers" in r["ruleId"]]
        assert len(tag_results) == 2  # MONSTER_SNARLED + EDIT_AND_PRAY

    def test_location_info(self, sample_results, sample_tags):
        sarif = generate_sarif_report(sample_results, sample_tags)
        results = sarif["runs"][0]["results"]
        for r in results:
            loc = r["locations"][0]["physicalLocation"]
            assert "artifactLocation" in loc
            assert "region" in loc

    def test_rules_defined(self, sample_results, sample_tags):
        sarif = generate_sarif_report(sample_results, sample_tags)
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) >= 3  # crap-threshold + 2 framework tags

    def test_write_to_file(self, sample_results, sample_tags, tmp_path):
        path = str(tmp_path / "report.sarif")
        write_sarif_report(sample_results, sample_tags, path)
        with open(path) as f:
            data = json.load(f)
        assert data["version"] == "2.1.0"


# ---------------------------------------------------------------------------
# GitHub Actions reporter tests
# ---------------------------------------------------------------------------

class TestGitHubActionsReporter:
    def test_annotations_generated(self, sample_results, sample_tags):
        annotations = generate_annotations(sample_results, sample_tags)
        assert len(annotations) >= 1  # At least CRAP threshold

    def test_annotation_format(self, sample_results, sample_tags):
        annotations = generate_annotations(sample_results, sample_tags)
        for ann in annotations:
            assert ann.startswith("::")
            assert "file=" in ann
            assert "line=" in ann

    def test_crap_violation_annotation(self, sample_results, sample_tags):
        annotations = generate_annotations(sample_results, sample_tags)
        crap_anns = [a for a in annotations if "CRAP threshold" in a]
        assert len(crap_anns) == 1

    def test_tag_annotations(self, sample_results, sample_tags):
        annotations = generate_annotations(sample_results, sample_tags)
        tag_anns = [a for a in annotations if "MONSTER_SNARLED" in a]
        assert len(tag_anns) == 1

    def test_summary_markdown(self, sample_results, sample_tags):
        summary = generate_summary(sample_results, sample_tags, phs_score=65.0)
        assert "## CRAPQuants" in summary
        assert "FAIL" in summary

    def test_clean_codebase_pass(self):
        results = [_make_file_result([_make_func("good", cc=2, cov=100.0)])]
        summary = generate_summary(results, {})
        assert "PASS" in summary
