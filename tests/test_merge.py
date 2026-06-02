"""Tests for merge layer — path normalization and complexity+coverage joining."""

import pytest

from crapquants.core.coverage_parser import FileCoverage
from crapquants.core.complexity import FunctionMetrics, FileMetrics
from crapquants.core.merge import (
    MergedFileResult,
    match_coverage_to_file,
    merge_file,
    normalize_path,
)


class TestNormalizePath:
    """Tests for path normalization."""

    def test_removes_dot_slash(self):
        assert normalize_path("./src/module.py") == "src/module.py"

    def test_normalizes_backslashes(self):
        assert normalize_path("src\\module.py") == "src/module.py"

    def test_resolves_dot_dot(self):
        result = normalize_path("src/sub/../module.py")
        assert result == "src/module.py"

    def test_already_normalized(self):
        assert normalize_path("src/module.py") == "src/module.py"

    def test_absolute_path(self):
        result = normalize_path("/home/user/project/src/module.py")
        assert "src/module.py" in result


class TestMatchCoverageToFile:
    """Tests for coverage-to-file matching."""

    def test_exact_match(self):
        cov = [
            FileCoverage("src/module.py", frozenset([1]), frozenset(), 1, 1, 100.0),
        ]
        result = match_coverage_to_file("src/module.py", cov)
        assert result is not None
        assert result.file_path == "src/module.py"

    def test_suffix_match(self):
        """Coverage has absolute path, source has relative."""
        cov = [
            FileCoverage(
                "/home/user/project/src/module.py",
                frozenset([1]), frozenset(), 1, 1, 100.0,
            ),
        ]
        result = match_coverage_to_file("src/module.py", cov)
        assert result is not None

    def test_no_match_returns_none(self):
        cov = [
            FileCoverage("src/other.py", frozenset([1]), frozenset(), 1, 1, 100.0),
        ]
        result = match_coverage_to_file("src/module.py", cov)
        assert result is None


class TestMergeFile:
    """Tests for merging file metrics with coverage."""

    @pytest.fixture
    def sample_file_metrics(self) -> FileMetrics:
        return FileMetrics(
            file_path="src/module.py",
            functions=[
                FunctionMetrics(
                    name="func_a",
                    file_path="src/module.py",
                    line_start=1,
                    line_end=10,
                    cyclomatic_complexity=5,
                    cognitive_complexity=3,
                    abc_assignments=2,
                    abc_branches=3,
                    abc_conditions=2,
                    abc_scalar=4.12,
                    line_count=10,
                    max_nesting_depth=2,
                    parameter_count=2,
                ),
                FunctionMetrics(
                    name="func_b",
                    file_path="src/module.py",
                    line_start=12,
                    line_end=25,
                    cyclomatic_complexity=15,
                    cognitive_complexity=12,
                    abc_assignments=5,
                    abc_branches=8,
                    abc_conditions=6,
                    abc_scalar=11.18,
                    line_count=14,
                    max_nesting_depth=4,
                    parameter_count=4,
                ),
            ],
            halstead_volume=100.0,
            halstead_difficulty=5.0,
            halstead_effort=500.0,
            maintainability_index=65.0,
            total_lines=30,
            code_lines=25,
            comment_lines=3,
            blank_lines=2,
        )

    @pytest.fixture
    def sample_coverage(self) -> list[FileCoverage]:
        return [
            FileCoverage(
                file_path="src/module.py",
                covered_lines=frozenset(range(1, 11)),  # Lines 1-10 covered
                missing_lines=frozenset(range(12, 26)),  # Lines 12-25 missing
                total_statements=25,
                covered_statements=10,
                coverage_percent=40.0,
            ),
        ]

    def test_merge_produces_results(self, sample_file_metrics, sample_coverage):
        result = merge_file(sample_file_metrics, sample_coverage)
        assert isinstance(result, MergedFileResult)
        assert len(result.functions) == 2

    def test_covered_function_crap(self, sample_file_metrics, sample_coverage):
        result = merge_file(sample_file_metrics, sample_coverage)
        func_a = result.functions[0]
        # func_a: CC=5, lines 1-10 fully covered → high coverage → low CRAP
        assert func_a.crap.crap_score < 30

    def test_uncovered_function_crap(self, sample_file_metrics, sample_coverage):
        result = merge_file(sample_file_metrics, sample_coverage)
        func_b = result.functions[1]
        # func_b: CC=15, lines 12-25 not covered → 0% coverage → high CRAP
        assert func_b.crap.is_crappy is True

    def test_pessimistic_missing_policy(self, sample_file_metrics):
        """No coverage data + pessimistic → 0% coverage for all functions."""
        result = merge_file(sample_file_metrics, [], missing_policy="pessimistic")
        for func in result.functions:
            assert func.coverage is None
            # 0% coverage means CRAP = CC² + CC
            assert func.crap.coverage == 0.0

    def test_optimistic_missing_policy(self, sample_file_metrics):
        """No coverage data + optimistic → 100% coverage."""
        result = merge_file(sample_file_metrics, [], missing_policy="optimistic")
        for func in result.functions:
            assert func.crap.coverage == 100.0

    def test_skip_missing_policy(self, sample_file_metrics):
        """No coverage data + skip → no functions in results."""
        result = merge_file(sample_file_metrics, [], missing_policy="skip")
        assert len(result.functions) == 0
