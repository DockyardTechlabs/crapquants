"""Tests for CRAPQuants CLI."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from crapquants.cli import app


runner = CliRunner()


@pytest.fixture
def sample_py_file(tmp_path: Path) -> Path:
    """Create a sample Python file to analyze."""
    f = tmp_path / "sample.py"
    f.write_text(
        "def simple_func(x):\n"
        "    return x + 1\n"
        "\n"
        "def complex_func(a, b, c, d, e):\n"
        "    if a > 0:\n"
        "        if b > 0:\n"
        "            if c > 0:\n"
        "                if d > 0:\n"
        "                    if e > 0:\n"
        "                        return a + b + c + d + e\n"
        "                    else:\n"
        "                        return a + b + c + d\n"
        "                else:\n"
        "                    return a + b + c\n"
        "            else:\n"
        "                return a + b\n"
        "        else:\n"
        "            return a\n"
        "    else:\n"
        "        return 0\n"
    )
    return f


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Create a directory with multiple Python files."""
    (tmp_path / "mod_a.py").write_text("def func_a():\n    return 1\n")
    (tmp_path / "mod_b.py").write_text(
        "def func_b(x):\n"
        "    if x > 0:\n"
        "        return x\n"
        "    return 0\n"
    )
    return tmp_path


class TestCLIAnalyze:
    def test_help_output(self):
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze Python code" in result.stdout

    def test_version_command(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.stdout

    def test_analyze_single_file_quick(self, sample_py_file):
        result = runner.invoke(app, ["analyze", str(sample_py_file), "--level", "quick"])
        # Exit code 1 if CRAPpy functions found (complex_func has high CC)
        assert result.exit_code in (0, 1)
        assert "CRAPQuants" in result.stdout

    def test_analyze_directory(self, sample_dir):
        result = runner.invoke(app, ["analyze", str(sample_dir)])
        assert result.exit_code in (0, 1)
        assert "CRAPQuants" in result.stdout

    def test_json_output(self, sample_py_file, tmp_path):
        output = tmp_path / "report.json"
        result = runner.invoke(app, [
            "analyze", str(sample_py_file),
            "-f", "json", "-o", str(output),
        ])
        assert result.exit_code in (0, 1)
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["tool"] == "crapquants"
        assert "glossary" in data
        assert data["summary"]["functions_analyzed"] >= 2

    def test_markdown_output(self, sample_py_file, tmp_path):
        output = tmp_path / "report.md"
        result = runner.invoke(app, [
            "analyze", str(sample_py_file),
            "-f", "markdown", "-o", str(output),
        ])
        assert result.exit_code in (0, 1)
        assert output.exists()
        content = output.read_text()
        assert "CRAPQuants Report" in content
        assert "How to Read" in content

    def test_sarif_output(self, sample_py_file, tmp_path):
        output = tmp_path / "report.sarif"
        result = runner.invoke(app, [
            "analyze", str(sample_py_file),
            "-f", "sarif", "-o", str(output),
        ])
        assert result.exit_code in (0, 1)
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["version"] == "2.1.0"

    def test_github_actions_output(self, sample_py_file):
        result = runner.invoke(app, [
            "analyze", str(sample_py_file),
            "-f", "github_actions",
        ])
        assert result.exit_code in (0, 1)
        assert "CRAPQuants" in result.stdout

    def test_nonexistent_path_fails(self):
        result = runner.invoke(app, ["analyze", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_custom_threshold(self, sample_py_file):
        result = runner.invoke(app, [
            "analyze", str(sample_py_file),
            "--threshold", "1000",
        ])
        # Very high threshold = nothing CRAPpy = exit 0
        assert result.exit_code == 0

    def test_show_passing_flag(self, sample_py_file):
        result = runner.invoke(app, [
            "analyze", str(sample_py_file),
            "--show-passing",
        ])
        assert result.exit_code in (0, 1)
        # Should show simple_func too
        assert "simple_func" in result.stdout

    def test_optimistic_missing_policy(self, sample_py_file):
        result = runner.invoke(app, [
            "analyze", str(sample_py_file),
            "--missing-policy", "optimistic",
        ])
        # Optimistic = 100% coverage assumed = lower CRAP scores
        assert result.exit_code in (0, 1)

    def test_exit_code_zero_for_clean_code(self, tmp_path):
        clean = tmp_path / "clean.py"
        clean.write_text("def hello():\n    return 'world'\n")
        result = runner.invoke(app, ["analyze", str(clean)])
        assert result.exit_code == 0

    def test_exit_code_one_for_crappy_code(self, sample_py_file):
        # complex_func has CC=10, 0% coverage → CRAP=110 → exit 1
        result = runner.invoke(app, [
            "analyze", str(sample_py_file),
            "--level", "quick",
        ])
        assert result.exit_code == 1

    def test_baseline_gate_passes_on_unchanged_crappy_code(self, sample_py_file, tmp_path):
        # Save a baseline that includes the pre-existing CRAPpy function,
        # then compare unchanged code against it: regression gate should PASS
        # even though CRAPpy functions exist (they're not NEW).
        baseline = tmp_path / "baseline.json"
        save = runner.invoke(app, [
            "analyze", str(sample_py_file), "--level", "quick",
            "--save-baseline", str(baseline),
        ])
        assert baseline.exists()

        result = runner.invoke(app, [
            "analyze", str(sample_py_file), "--level", "quick",
            "--baseline", str(baseline),
        ])
        # Pre-existing CRAPpy functions must NOT fail the build under baseline mode
        assert result.exit_code == 0

    def test_baseline_gate_fails_on_new_regression(self, sample_py_file, tmp_path):
        # Baseline from the original file, then ADD a new CRAPpy function
        # and compare: regression gate should FAIL (exit 1).
        baseline = tmp_path / "baseline.json"
        runner.invoke(app, [
            "analyze", str(sample_py_file), "--level", "quick",
            "--save-baseline", str(baseline),
        ])
        # Append a new awful function to introduce a regression
        with open(sample_py_file, "a") as fh:
            fh.write(
                "\ndef new_monster(a, b, c, d):\n"
                "    if a:\n        if b:\n            if c:\n"
                "                if d:\n                    for x in range(a):\n"
                "                        if x > b:\n                            return x\n"
                "    return None\n"
            )
        result = runner.invoke(app, [
            "analyze", str(sample_py_file), "--level", "quick",
            "--baseline", str(baseline),
        ])
        assert result.exit_code == 1
