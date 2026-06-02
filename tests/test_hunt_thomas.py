"""Tests for Hunt & Thomas Framework."""

import pytest

from crapquants.core.complexity import FunctionMetrics
from crapquants.core.crap import CRAPResult, calculate_crap
from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.hunt_thomas import (
    CodebaseHealth,
    analyze,
    compute_pragmatic_health_score,
)


def _make_result(cc=5, cov=50.0, nesting=2, lines=20, params=2, abc_c=3):
    crap_score = calculate_crap(cc, cov)
    return MergedFunctionResult(
        metrics=FunctionMetrics(
            name="test_func", file_path="test.py", line_start=1, line_end=lines,
            cyclomatic_complexity=cc, cognitive_complexity=cc,
            abc_assignments=3, abc_branches=5, abc_conditions=abc_c,
            abc_scalar=7.0, line_count=lines,
            max_nesting_depth=nesting, parameter_count=params,
        ),
        coverage=None,
        crap=CRAPResult(
            function_name="test_func", file_path="test.py", line_number=1,
            complexity=cc, coverage=cov, crap_score=crap_score,
            crapload=0, is_crappy=crap_score > 30,
            min_coverage_needed=0.0, complexity_threshold_exceeded=cc >= 31,
        ),
    )


class TestPragmaticHealthScore:
    def test_perfect_health(self):
        health = CodebaseHealth(total_functions=100)
        assert compute_pragmatic_health_score(health) == 100.0

    def test_empty_codebase(self):
        health = CodebaseHealth()
        assert compute_pragmatic_health_score(health) == 100.0

    def test_all_crappy_reduces_score(self):
        health = CodebaseHealth(total_functions=10, crappy_functions=10)
        score = compute_pragmatic_health_score(health)
        assert score < 75.0

    def test_broken_windows_reduce_score(self):
        health = CodebaseHealth(total_functions=10, broken_window_count=5)
        score = compute_pragmatic_health_score(health)
        assert score < 80.0

    def test_coincidence_reduces_score(self):
        health = CodebaseHealth(total_functions=10, coincidence_count=3)
        score = compute_pragmatic_health_score(health)
        assert score < 90.0

    def test_score_clamped_to_zero(self):
        health = CodebaseHealth(
            total_functions=5, crappy_functions=5,
            broken_window_count=5, coincidence_count=5,
            no_safety_net_count=5,
        )
        score = compute_pragmatic_health_score(health)
        assert score >= 0.0


class TestHuntThomasAnalyze:
    def test_clean_function_no_critical_tags(self):
        result = _make_result(cc=3, cov=100.0)
        tags = analyze(result)
        critical = [t for t in tags if t.severity.value == "critical"]
        assert len(critical) == 0

    def test_coincidence_code_detected(self):
        result = _make_result(cc=10, cov=0.0, nesting=3)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "COINCIDENCE_CODE" in tag_ids

    def test_no_safety_net_detected(self):
        result = _make_result(cc=8, cov=0.0)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "NO_SAFETY_NET" in tag_ids

    def test_no_contracts_detected(self):
        result = _make_result(cc=12, cov=50.0, abc_c=1)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "NO_CONTRACTS" in tag_ids

    def test_broken_window_detected(self):
        result = _make_result(cc=10, cov=0.0)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "BROKEN_WINDOW" in tag_ids

    def test_refactor_ready_detected(self):
        # Need CRAP > 30 with coverage >= 70%
        # CC=25, cov=72% → CRAP = 625×0.022 + 25 = 38.6 (crappy + high cov)
        result = _make_result(cc=25, cov=72.0)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "REFACTOR_READY" in tag_ids

    def test_coincidence_has_recommendations(self):
        result = _make_result(cc=10, cov=0.0, nesting=3)
        tags = analyze(result)
        coincidence = [t for t in tags if t.tag_id == "COINCIDENCE_CODE"]
        assert len(coincidence) == 1
        assert len(coincidence[0].recommendations) >= 2
