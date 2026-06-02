"""Tests for Feathers Framework diagnostic analysis."""

import pytest

from crapquants.core.complexity import FunctionMetrics
from crapquants.core.crap import CRAPResult
from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.feathers import (
    analyze,
    classify_monster,
    compute_frs,
    compute_testability_index,
    monster_multiplier,
)


def _make_result(
    cc: int = 5, cov: float = 50.0, nesting: int = 2,
    lines: int = 20, params: int = 2,
) -> MergedFunctionResult:
    """Helper to create test MergedFunctionResult."""
    from crapquants.core.crap import calculate_crap
    crap_score = calculate_crap(cc, cov)
    return MergedFunctionResult(
        metrics=FunctionMetrics(
            name="test_func", file_path="test.py", line_start=1, line_end=lines,
            cyclomatic_complexity=cc, cognitive_complexity=cc,
            abc_assignments=3, abc_branches=5, abc_conditions=cc,
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


class TestClassifyMonster:
    def test_low_cc_not_monster(self):
        assert classify_monster(5, 2, 20) is None

    def test_snarled(self):
        assert classify_monster(15, 5, 30) == "SNARLED"

    def test_bulleted(self):
        assert classify_monster(12, 2, 60) == "BULLETED"

    def test_complex_but_compact(self):
        assert classify_monster(12, 2, 20) == "COMPLEX_BUT_COMPACT"


class TestMonsterMultiplier:
    def test_snarled_multiplier(self):
        assert monster_multiplier("SNARLED") == 1.5

    def test_bulleted_multiplier(self):
        assert monster_multiplier("BULLETED") == 1.2

    def test_none_multiplier(self):
        assert monster_multiplier(None) == 1.0


class TestComputeFRS:
    def test_basic_frs(self):
        frs = compute_frs(30.0, None, 0, 1)
        assert frs == 30.0

    def test_snarled_amplifies(self):
        frs = compute_frs(30.0, "SNARLED", 0, 1)
        assert frs == 45.0  # 30 × 1.5

    def test_dependency_depth_amplifies(self):
        frs = compute_frs(30.0, None, 5, 1)
        assert frs == 45.0  # 30 × 1.5

    def test_multi_responsibility_amplifies(self):
        frs = compute_frs(30.0, None, 0, 2)
        assert frs == 39.0  # 30 × 1.3


class TestTestabilityIndex:
    def test_perfect_testability(self):
        assert compute_testability_index(0, False, False) == 100.0

    def test_dep_depth_reduces(self):
        assert compute_testability_index(3, False, False) == 70.0

    def test_sensing_problem_reduces(self):
        assert compute_testability_index(0, True, False) == 85.0

    def test_separation_problem_reduces(self):
        assert compute_testability_index(0, False, True) == 80.0

    def test_all_problems(self):
        ti = compute_testability_index(5, True, True)
        assert ti == 15.0  # 100 - 50 - 15 - 20

    def test_clamped_to_zero(self):
        ti = compute_testability_index(10, True, True)
        assert ti == 0.0


class TestFeathersAnalyze:
    def test_clean_function_no_tags(self):
        result = _make_result(cc=3, cov=100.0, nesting=1, lines=10, params=1)
        tags = analyze(result)
        assert len(tags) == 0

    def test_snarled_monster_detected(self):
        result = _make_result(cc=15, cov=0.0, nesting=5, lines=30, params=2)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "MONSTER_SNARLED" in tag_ids

    def test_bulleted_monster_detected(self):
        result = _make_result(cc=12, cov=50.0, nesting=2, lines=60, params=2)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "MONSTER_BULLETED" in tag_ids

    def test_edit_and_pray_detected(self):
        result = _make_result(cc=8, cov=0.0, nesting=2, lines=20, params=1)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "EDIT_AND_PRAY" in tag_ids

    def test_characterization_needed(self):
        result = _make_result(cc=10, cov=0.0, nesting=2, lines=20, params=1)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "CHARACTERIZATION_NEEDED" in tag_ids

    def test_legacy_dilemma(self):
        result = _make_result(cc=15, cov=0.0, nesting=3, lines=30, params=5)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "LEGACY_DILEMMA" in tag_ids

    def test_refactor_mandatory(self):
        result = _make_result(cc=35, cov=100.0, nesting=2, lines=50, params=2)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "REFACTOR_MANDATORY" in tag_ids

    def test_tags_have_recommendations(self):
        result = _make_result(cc=15, cov=0.0, nesting=5, lines=30, params=2)
        tags = analyze(result)
        for tag in tags:
            if tag.tag_id == "MONSTER_SNARLED":
                assert len(tag.recommendations) > 0
