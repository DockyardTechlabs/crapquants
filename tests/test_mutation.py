"""Tests for mutation testing module — mutmut runner and result parsing."""

import pytest

from crapquants.mutation.mutmut_runner import (
    MutantResult,
    MutationReport,
    _extract_count,
    _parse_results_output,
    format_mutation_summary,
    is_mutmut_available,
)


class TestExtractCount:
    def test_killed_count(self):
        assert _extract_count("Killed (10)") == 10

    def test_survived_with_emoji(self):
        assert _extract_count("Survived 🙁 (3)") == 3

    def test_timeout_count(self):
        assert _extract_count("Timeout ⏰ (2)") == 2

    def test_no_parens(self):
        assert _extract_count("No count here") is None

    def test_empty_parens(self):
        assert _extract_count("Empty ()") is None


class TestParseResultsOutput:
    def test_parse_clean_results(self):
        output = "Killed (5)\nSurvived 🙁 (0)\nTimeout ⏰ (0)\n"
        report = _parse_results_output(output)
        assert report.killed == 5
        assert report.survived == 0
        assert report.mutation_score == 100.0

    def test_parse_with_survivors(self):
        output = (
            "Survived 🙁 (2)\n"
            "---- src/core.py (line 15) ----\n"
            "1\n"
            "---- src/core.py (line 28) ----\n"
            "2\n"
            "\n"
            "Killed (8)\n"
        )
        report = _parse_results_output(output)
        assert report.killed == 8
        assert report.survived == 2
        assert report.total_mutants == 10
        assert report.mutation_score == 80.0
        assert len(report.survived_mutants) == 2
        assert report.survived_mutants[0].file_path == "src/core.py"
        assert report.survived_mutants[0].line == 15

    def test_parse_empty_output(self):
        report = _parse_results_output("")
        assert report.total_mutants == 0
        assert report.mutation_score == 0.0

    def test_parse_all_sections(self):
        output = (
            "Killed (10)\n"
            "Survived 🙁 (3)\n"
            "Timeout ⏰ (1)\n"
            "Suspicious (1)\n"
            "Skipped (5)\n"
        )
        report = _parse_results_output(output)
        assert report.killed == 10
        assert report.survived == 3
        assert report.timeout == 1
        assert report.suspicious == 1
        assert report.skipped == 5
        assert report.total_mutants == 20

    def test_mutation_score_calculation(self):
        output = "Killed (7)\nSurvived 🙁 (3)\n"
        report = _parse_results_output(output)
        assert report.mutation_score == 70.0


class TestMutationReport:
    def test_perfect_score(self):
        report = MutationReport(
            total_mutants=10, killed=10, survived=0,
            timeout=0, suspicious=0, skipped=0,
            mutation_score=100.0, survived_mutants=[],
        )
        assert report.mutation_score == 100.0

    def test_zero_mutants(self):
        report = MutationReport(
            total_mutants=0, killed=0, survived=0,
            timeout=0, suspicious=0, skipped=0,
            mutation_score=0.0, survived_mutants=[],
        )
        assert report.total_mutants == 0


class TestFormatSummary:
    def test_summary_contains_score(self):
        report = MutationReport(
            total_mutants=10, killed=8, survived=2,
            timeout=0, suspicious=0, skipped=0,
            mutation_score=80.0,
            survived_mutants=[
                MutantResult(1, "survived", "src/mod.py", 15),
                MutantResult(2, "survived", "src/mod.py", 28),
            ],
        )
        summary = format_mutation_summary(report)
        assert "80.0%" in summary
        assert "Killed: 8" in summary
        assert "Survived: 2" in summary
        assert "src/mod.py:15" in summary

    def test_summary_no_survivors(self):
        report = MutationReport(
            total_mutants=5, killed=5, survived=0,
            timeout=0, suspicious=0, skipped=0,
            mutation_score=100.0, survived_mutants=[],
        )
        summary = format_mutation_summary(report)
        assert "100.0%" in summary
        assert "blind spots" not in summary


class TestMutmutAvailability:
    def test_availability_check(self):
        result = is_mutmut_available()
        assert isinstance(result, bool)
