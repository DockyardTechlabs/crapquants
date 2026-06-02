"""Tests for Ousterhout Framework diagnostic analysis."""

import pytest

from crapquants.core.complexity import FunctionMetrics
from crapquants.core.crap import CRAPResult, calculate_crap
from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.ousterhout import (
    analyze,
    compute_depth_ratio,
    compute_cognitive_load_proxy,
    compute_obscurity_score,
    compute_ors,
)


def _make_result(
    name: str = "test_func", cc: int = 5, cogc: int = 5, cov: float = 50.0,
    nesting: int = 2, lines: int = 20, params: int = 2,
    abc_a: int = 3, abc_b: int = 5, abc_c: int = 3,
) -> MergedFunctionResult:
    crap_score = calculate_crap(cc, cov)
    return MergedFunctionResult(
        metrics=FunctionMetrics(
            name=name, file_path="test.py", line_start=1, line_end=lines,
            cyclomatic_complexity=cc, cognitive_complexity=cogc,
            abc_assignments=abc_a, abc_branches=abc_b, abc_conditions=abc_c,
            abc_scalar=7.0, line_count=lines,
            max_nesting_depth=nesting, parameter_count=params,
        ),
        coverage=None,
        crap=CRAPResult(
            function_name=name, file_path="test.py", line_number=1,
            complexity=cc, coverage=cov, crap_score=crap_score,
            crapload=0, is_crappy=crap_score > 30,
            min_coverage_needed=0.0, complexity_threshold_exceeded=cc >= 31,
        ),
    )


class TestDepthRatio:
    def test_deep_function(self):
        assert compute_depth_ratio(100, 2) > 10.0

    def test_shallow_function(self):
        assert compute_depth_ratio(3, 5) < 3.0

    def test_zero_params(self):
        # interface_complexity = max(1, 0+1) = 1
        assert compute_depth_ratio(10, 0) == 10.0


class TestCognitiveLoadProxy:
    def test_simple(self):
        assert compute_cognitive_load_proxy(3, 2, 1, 1) == 7

    def test_complex(self):
        assert compute_cognitive_load_proxy(15, 20, 6, 4) == 45


class TestObscurityScore:
    def test_fully_documented(self):
        assert compute_obscurity_score(True, True, 0) == 0

    def test_no_docstring(self):
        assert compute_obscurity_score(False, True, 0) == 2

    def test_no_types(self):
        assert compute_obscurity_score(True, False, 0) == 1

    def test_vague_names_add(self):
        assert compute_obscurity_score(True, True, 3) == 3


class TestComputeORS:
    def test_deep_clean_module(self):
        ors = compute_ors(10.0, 15.0, 0, 0)
        assert ors < 15.0  # Minimal amplification

    def test_shallow_amplifies(self):
        ors = compute_ors(10.0, 1.0, 0, 0)
        assert ors > 10.0  # Shallow = amplified

    def test_obscurity_amplifies(self):
        ors = compute_ors(10.0, 10.0, 5, 0)
        assert ors > 10.0

    def test_red_flags_amplify(self):
        ors = compute_ors(10.0, 10.0, 0, 3)
        assert ors > 10.0


class TestOusterhoutAnalyze:
    def test_clean_function_minimal_tags(self):
        result = _make_result(cc=3, cogc=2, cov=100.0, lines=20, params=2)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "NONOBVIOUS" not in tag_ids

    def test_shallow_module_detected(self):
        result = _make_result(cc=1, cogc=0, cov=100.0, lines=2, params=3)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "SHALLOW_MODULE" in tag_ids

    def test_overexposed_api_detected(self):
        result = _make_result(params=6)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "OVEREXPOSED_API" in tag_ids

    def test_pass_through_detected(self):
        result = _make_result(cc=1, cogc=0, lines=2, params=1, abc_b=1, abc_a=0, abc_c=0)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "PASS_THROUGH" in tag_ids

    def test_vague_name_detected(self):
        result = _make_result(name="process_data")
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "VAGUE_NAMING" in tag_ids

    def test_hard_to_name_detected(self):
        long_name = "process_and_validate_then_transform_all_records_in_batch"
        result = _make_result(name=long_name)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "HARD_TO_NAME" in tag_ids

    def test_nonobvious_detected(self):
        result = _make_result(
            name="process_data", cc=8, cogc=12, nesting=4, params=5,
        )
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "NONOBVIOUS" in tag_ids

    def test_deep_module_positive_signal(self):
        result = _make_result(cc=3, cogc=2, cov=100.0, lines=50, params=1)
        tags = analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "DEEP_MODULE" in tag_ids
