"""Tests for Fowler Framework."""

import pytest
from crapquants.core.complexity import FunctionMetrics
from crapquants.core.crap import CRAPResult, calculate_crap
from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.fowler import analyze, get_refactorings_for_tag


def _make_result(cc=5, cov=50.0, cogc=5, nesting=2, lines=20, params=2,
                 abc_a=3, abc_b=5, abc_c=3):
    crap_score = calculate_crap(cc, cov)
    return MergedFunctionResult(
        metrics=FunctionMetrics(
            name="test_func", file_path="test.py", line_start=1, line_end=lines,
            cyclomatic_complexity=cc, cognitive_complexity=cogc,
            abc_assignments=abc_a, abc_branches=abc_b, abc_conditions=abc_c,
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


class TestFowlerAnalyze:
    def test_clean_function_no_tags(self):
        result = _make_result(cc=3, cov=100.0, lines=10, params=2)
        tags = analyze(result)
        assert len(tags) == 0

    def test_long_method_by_lines(self):
        result = _make_result(cc=5, lines=40)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "LONG_METHOD" in tag_ids

    def test_long_method_by_cc(self):
        result = _make_result(cc=12, lines=20)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "LONG_METHOD" in tag_ids

    def test_long_param_list(self):
        result = _make_result(params=6)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "LONG_PARAM_LIST" in tag_ids

    def test_lazy_class(self):
        result = _make_result(cc=1, lines=2, abc_b=1, abc_a=0)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "LAZY_CLASS" in tag_ids

    def test_comments_as_deodorant(self):
        result = _make_result(cc=10, cogc=18, lines=30)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "COMMENTS_AS_DEODORANT" in tag_ids

    def test_long_method_gets_decompose_for_nesting(self):
        result = _make_result(cc=12, lines=40, nesting=4, params=5)
        tags = analyze(result)
        long_method = [t for t in tags if t.tag_id == "LONG_METHOD"][0]
        rec_names = [r.action for r in long_method.recommendations]
        assert "Decompose Conditional" in rec_names
        assert "Introduce Parameter Object" in rec_names


class TestRefactoringMap:
    def test_known_tag_returns_recommendations(self):
        recs = get_refactorings_for_tag("MONSTER_SNARLED")
        assert len(recs) > 0

    def test_unknown_tag_returns_empty(self):
        recs = get_refactorings_for_tag("NONEXISTENT_TAG")
        assert len(recs) == 0

    def test_broken_window_has_extract_method(self):
        recs = get_refactorings_for_tag("BROKEN_WINDOW")
        actions = [r.action for r in recs]
        assert "Extract Method" in actions

    def test_coincidence_has_multiple_recs(self):
        recs = get_refactorings_for_tag("COINCIDENCE_CODE")
        assert len(recs) >= 2
