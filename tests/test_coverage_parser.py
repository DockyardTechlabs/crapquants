"""Tests for coverage data parsing (JSON, LCOV formats)."""

import json
import tempfile
from pathlib import Path

import pytest

from crapquants.core.coverage_parser import (
    FileCoverage,
    FunctionCoverage,
    estimate_function_coverage,
    parse_coverage_json,
    parse_coverage_lcov,
)


@pytest.fixture
def sample_coverage_json(tmp_path: Path) -> Path:
    """Create a sample coverage.py JSON report."""
    data = {
        "meta": {"version": "7.0"},
        "files": {
            "src/module_a.py": {
                "executed_lines": [1, 2, 3, 5, 6, 10, 11],
                "missing_lines": [7, 8, 12, 13],
                "summary": {
                    "num_statements": 11,
                    "covered_lines": 7,
                    "percent_covered": 63.64,
                },
            },
            "src/module_b.py": {
                "executed_lines": [1, 2, 3, 4, 5],
                "missing_lines": [],
                "summary": {
                    "num_statements": 5,
                    "covered_lines": 5,
                    "percent_covered": 100.0,
                },
            },
        },
    }
    json_path = tmp_path / "coverage.json"
    json_path.write_text(json.dumps(data))
    return json_path


@pytest.fixture
def sample_coverage_lcov(tmp_path: Path) -> Path:
    """Create a sample LCOV report."""
    lcov_content = (
        "SF:src/module_a.py\n"
        "DA:1,1\n"
        "DA:2,1\n"
        "DA:3,1\n"
        "DA:5,1\n"
        "DA:6,1\n"
        "DA:7,0\n"
        "DA:8,0\n"
        "DA:10,1\n"
        "DA:11,1\n"
        "DA:12,0\n"
        "DA:13,0\n"
        "LF:11\n"
        "LH:7\n"
        "end_of_record\n"
    )
    lcov_path = tmp_path / "coverage.lcov"
    lcov_path.write_text(lcov_content)
    return lcov_path


class TestParseCoverageJson:
    """Tests for JSON coverage parsing."""

    def test_parse_valid_json(self, sample_coverage_json: Path):
        results = parse_coverage_json(sample_coverage_json)
        assert len(results) == 2

    def test_file_coverage_fields(self, sample_coverage_json: Path):
        results = parse_coverage_json(sample_coverage_json)
        module_a = [r for r in results if "module_a" in r.file_path][0]
        assert module_a.total_statements == 11
        assert module_a.covered_statements == 7
        assert module_a.coverage_percent == 63.64
        assert 1 in module_a.covered_lines
        assert 7 in module_a.missing_lines

    def test_full_coverage_file(self, sample_coverage_json: Path):
        results = parse_coverage_json(sample_coverage_json)
        module_b = [r for r in results if "module_b" in r.file_path][0]
        assert module_b.coverage_percent == 100.0
        assert len(module_b.missing_lines) == 0

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_coverage_json("/nonexistent/coverage.json")

    def test_invalid_json_format_raises(self, tmp_path: Path):
        bad_json = tmp_path / "bad.json"
        bad_json.write_text('{"no_files_key": true}')
        with pytest.raises(ValueError, match="files"):
            parse_coverage_json(bad_json)


class TestParseCoverageLcov:
    """Tests for LCOV coverage parsing."""

    def test_parse_valid_lcov(self, sample_coverage_lcov: Path):
        results = parse_coverage_lcov(sample_coverage_lcov)
        assert len(results) == 1

    def test_lcov_coverage_values(self, sample_coverage_lcov: Path):
        results = parse_coverage_lcov(sample_coverage_lcov)
        r = results[0]
        assert r.file_path == "src/module_a.py"
        assert r.total_statements == 11
        assert r.covered_statements == 7
        assert 1 in r.covered_lines
        assert 7 in r.missing_lines

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_coverage_lcov("/nonexistent/coverage.lcov")


class TestEstimateFunctionCoverage:
    """Tests for per-function coverage estimation."""

    def test_fully_covered_function(self):
        fc = FileCoverage(
            file_path="test.py",
            covered_lines=frozenset([1, 2, 3, 4, 5]),
            missing_lines=frozenset(),
            total_statements=5,
            covered_statements=5,
            coverage_percent=100.0,
        )
        result = estimate_function_coverage(fc, "func", 1, 5)
        assert result.coverage_percent == 100.0

    def test_uncovered_function(self):
        fc = FileCoverage(
            file_path="test.py",
            covered_lines=frozenset(),
            missing_lines=frozenset([1, 2, 3]),
            total_statements=3,
            covered_statements=0,
            coverage_percent=0.0,
        )
        result = estimate_function_coverage(fc, "func", 1, 3)
        assert result.coverage_percent == 0.0

    def test_partial_coverage(self):
        fc = FileCoverage(
            file_path="test.py",
            covered_lines=frozenset([1, 2, 5, 6]),
            missing_lines=frozenset([3, 4, 7, 8]),
            total_statements=8,
            covered_statements=4,
            coverage_percent=50.0,
        )
        # Function spans lines 5-8: covered=[5,6], missing=[7,8] → 50%
        result = estimate_function_coverage(fc, "func", 5, 8)
        assert result.coverage_percent == 50.0

    def test_no_statement_data_returns_zero(self):
        fc = FileCoverage(
            file_path="test.py",
            covered_lines=frozenset([1, 2]),
            missing_lines=frozenset([3]),
            total_statements=3,
            covered_statements=2,
            coverage_percent=66.67,
        )
        # Function at lines 100-110 — no overlap with coverage data
        result = estimate_function_coverage(fc, "func", 100, 110)
        assert result.coverage_percent == 0.0

    def test_result_fields(self):
        fc = FileCoverage(
            file_path="myfile.py",
            covered_lines=frozenset([10, 11, 12]),
            missing_lines=frozenset([13]),
            total_statements=4,
            covered_statements=3,
            coverage_percent=75.0,
        )
        result = estimate_function_coverage(fc, "my_func", 10, 13)
        assert result.function_name == "my_func"
        assert result.file_path == "myfile.py"
        assert result.line_start == 10
        assert result.line_end == 13
        assert result.coverage_percent == 75.0
