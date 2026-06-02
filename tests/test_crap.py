"""
Tests for the CRAP formula implementation.

Validates against known values from Crap4J documentation and
the complexity-coverage threshold table.
"""

import pytest

from crapquants.core.crap import (
    CRAPResult,
    calculate_crap,
    calculate_crapload,
    compute_crap_result,
    min_coverage_for_threshold,
)


class TestCalculateCrap:
    """Tests for the core CRAP formula."""

    def test_zero_complexity_zero_coverage(self):
        """CC=0, cov=0% → CRAP=0."""
        assert calculate_crap(0, 0.0) == 0.0

    def test_zero_complexity_full_coverage(self):
        """CC=0, cov=100% → CRAP=0."""
        assert calculate_crap(0, 100.0) == 0.0

    def test_simple_function_full_coverage(self):
        """CC=1, cov=100% → CRAP=1 (just the comp term, cov_factor=0)."""
        assert calculate_crap(1, 100.0) == 1.0

    def test_simple_function_no_coverage(self):
        """CC=1, cov=0% → CRAP=1²×1³+1=2."""
        assert calculate_crap(1, 0.0) == 2.0

    def test_moderate_complexity_no_coverage(self):
        """CC=10, cov=0% → CRAP=100×1+10=110."""
        assert calculate_crap(10, 0.0) == 110.0

    def test_moderate_complexity_full_coverage(self):
        """CC=10, cov=100% → CRAP=100×0+10=10."""
        assert calculate_crap(10, 100.0) == 10.0

    def test_moderate_complexity_half_coverage(self):
        """CC=10, cov=50% → CRAP=100×0.125+10=22.5."""
        assert calculate_crap(10, 50.0) == 22.5

    def test_high_complexity_no_coverage(self):
        """CC=20, cov=0% → CRAP=400+20=420."""
        assert calculate_crap(20, 0.0) == 420.0

    def test_high_complexity_high_coverage(self):
        """CC=20, cov=90% → CRAP=400×0.001+20=20.4."""
        assert calculate_crap(20, 90.0) == 20.4

    def test_threshold_boundary_cc10_42pct(self):
        """CC=10 at 42% coverage should be near threshold 30 (from Crap4J table)."""
        score = calculate_crap(10, 42.0)
        assert 25.0 < score < 35.0  # Near threshold

    def test_threshold_boundary_cc5_0pct(self):
        """CC=5, cov=0% → CRAP=25+5=30. Exactly at threshold."""
        assert calculate_crap(5, 0.0) == 30.0

    def test_negative_complexity_raises(self):
        """Negative complexity must raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_crap(-1, 50.0)

    def test_coverage_over_100_raises(self):
        """Coverage over 100% must raise ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 100.0"):
            calculate_crap(5, 101.0)

    def test_coverage_negative_raises(self):
        """Negative coverage must raise ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 100.0"):
            calculate_crap(5, -1.0)

    def test_extreme_complexity(self):
        """CC=50, cov=0% → CRAP=2500+50=2550."""
        assert calculate_crap(50, 0.0) == 2550.0

    def test_coverage_precision(self):
        """Verify result is rounded to 2 decimal places."""
        result = calculate_crap(7, 33.3)
        assert result == round(result, 2)


class TestMinCoverageForThreshold:
    """Tests for the complexity-coverage threshold table."""

    def test_cc0_needs_0_coverage(self):
        assert min_coverage_for_threshold(0) == 0.0

    def test_cc5_needs_0_coverage(self):
        """CC=5 at 0% → CRAP=30, exactly at threshold."""
        assert min_coverage_for_threshold(5) == 0.0

    def test_cc10_needs_around_42(self):
        """CC=10 should need approximately 42% coverage."""
        min_cov = min_coverage_for_threshold(10)
        assert 35.0 < min_cov < 50.0

    def test_cc15_needs_around_57(self):
        """CC=15 should need approximately 57% coverage."""
        min_cov = min_coverage_for_threshold(15)
        assert 50.0 < min_cov < 65.0

    def test_cc20_needs_around_71(self):
        """CC=20 should need approximately 71% coverage."""
        min_cov = min_coverage_for_threshold(20)
        assert 65.0 < min_cov < 78.0

    def test_cc25_needs_around_80(self):
        """CC=25 should need approximately 80% coverage."""
        min_cov = min_coverage_for_threshold(25)
        assert 75.0 < min_cov < 88.0

    def test_cc31_returns_100(self):
        """CC=31+ means refactor required, returns 100%."""
        assert min_coverage_for_threshold(31) == 100.0

    def test_cc50_returns_100(self):
        """CC=50 also returns 100% (refactor mandatory)."""
        assert min_coverage_for_threshold(50) == 100.0


class TestCalculateCrapload:
    """Tests for CRAPload — minimum effort estimation."""

    def test_below_threshold_returns_zero(self):
        """CRAPload is 0 when CRAP is below threshold."""
        assert calculate_crapload(25.0, 10, 60.0) == 0

    def test_at_threshold_returns_zero(self):
        """CRAPload is 0 when CRAP equals threshold."""
        assert calculate_crapload(30.0, 5, 0.0) == 0

    def test_above_threshold_returns_positive(self):
        """CRAPload must be positive when CRAP exceeds threshold."""
        crapload = calculate_crapload(110.0, 10, 0.0)
        assert crapload > 0

    def test_high_cc_no_coverage(self):
        """CC=20, cov=0% → all paths uncovered, CRAPload=20."""
        crapload = calculate_crapload(420.0, 20, 0.0)
        assert crapload == 20  # 20 uncovered paths, no refactoring (CC < 31)

    def test_cc31_adds_refactoring(self):
        """CC=31 triggers refactoring count in CRAPload."""
        crapload = calculate_crapload(1000.0, 31, 0.0)
        assert crapload > 31  # uncovered paths + refactoring effort


class TestComputeCrapResult:
    """Tests for the complete CRAP result computation."""

    def test_returns_crap_result(self):
        """compute_crap_result should return a CRAPResult dataclass."""
        result = compute_crap_result("my_func", "test.py", 10, 5, 80.0)
        assert isinstance(result, CRAPResult)

    def test_crappy_function_flagged(self):
        """CC=10, cov=0% → CRAP=110, is_crappy=True."""
        result = compute_crap_result("bad_func", "test.py", 1, 10, 0.0)
        assert result.is_crappy is True
        assert result.crap_score == 110.0
        assert result.crapload > 0

    def test_clean_function_not_flagged(self):
        """CC=3, cov=100% → CRAP=3, is_crappy=False."""
        result = compute_crap_result("good_func", "test.py", 1, 3, 100.0)
        assert result.is_crappy is False
        assert result.crap_score == 3.0
        assert result.crapload == 0

    def test_cc31_flags_complexity_exceeded(self):
        """CC=31 should set complexity_threshold_exceeded=True."""
        result = compute_crap_result("monster", "test.py", 1, 31, 100.0)
        assert result.complexity_threshold_exceeded is True

    def test_result_fields_populated(self):
        """All fields in CRAPResult must be populated."""
        result = compute_crap_result("func", "file.py", 42, 8, 55.0)
        assert result.function_name == "func"
        assert result.file_path == "file.py"
        assert result.line_number == 42
        assert result.complexity == 8
        assert result.coverage == 55.0
        assert result.crap_score > 0
        assert result.min_coverage_needed >= 0.0

    def test_frozen_dataclass(self):
        """CRAPResult should be immutable (frozen=True)."""
        result = compute_crap_result("func", "file.py", 1, 5, 50.0)
        with pytest.raises(AttributeError):
            result.crap_score = 999.0
