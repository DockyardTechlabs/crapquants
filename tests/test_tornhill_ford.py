"""Tests for Tornhill and Ford Frameworks."""

import pytest
from crapquants.core.complexity import FunctionMetrics
from crapquants.core.crap import CRAPResult, calculate_crap
from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.tornhill import analyze as tornhill_analyze, compute_tbs, analyze_with_git, GitContext
from crapquants.frameworks.ford import analyze as ford_analyze, BUILTIN_FITNESS_FUNCTIONS


def _make_result(cc=5, cogc=5, cov=50.0, nesting=2, lines=20, params=2,
                 abc_a=3, abc_b=5, abc_c=3, abc_scalar=7.0):
    crap_score = calculate_crap(cc, cov)
    return MergedFunctionResult(
        metrics=FunctionMetrics(
            name="test_func", file_path="test.py", line_start=1, line_end=lines,
            cyclomatic_complexity=cc, cognitive_complexity=cogc,
            abc_assignments=abc_a, abc_branches=abc_b, abc_conditions=abc_c,
            abc_scalar=abc_scalar, line_count=lines,
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


class TestTornhillTBS:
    def test_baseline_tbs(self):
        # tf=3: knowledge_weight = 1.0 + (1/3)*0.3 = 1.1
        tbs = compute_tbs(30.0)
        assert tbs == 33.0  # 30 × 1.0 × 1.0 × 1.1 × 1.0 = 33.0

    def test_high_churn_amplifies(self):
        tbs_low = compute_tbs(30.0, change_frequency=0)
        tbs_high = compute_tbs(30.0, change_frequency=40)
        assert tbs_high > tbs_low

    def test_deteriorating_amplifies(self):
        tbs_stable = compute_tbs(30.0, trend="STABLE")
        tbs_deteriorating = compute_tbs(30.0, trend="DETERIORATING")
        assert tbs_deteriorating > tbs_stable

    def test_improving_reduces(self):
        tbs_stable = compute_tbs(30.0, trend="STABLE")
        tbs_improving = compute_tbs(30.0, trend="IMPROVING")
        assert tbs_improving < tbs_stable

    def test_low_truck_factor_amplifies(self):
        tbs_safe = compute_tbs(30.0, truck_factor=5)
        tbs_risky = compute_tbs(30.0, truck_factor=1)
        assert tbs_risky > tbs_safe


class TestTornhillAnalyze:
    def test_clean_function_no_tags(self):
        result = _make_result(cc=3, cogc=3, cov=100.0)
        tags = tornhill_analyze(result)
        assert len(tags) == 0

    def test_dormant_hotspot_detected(self):
        result = _make_result(cc=15, cogc=15, cov=0.0)
        tags = tornhill_analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "HOTSPOT_DORMANT" in tag_ids

    def test_knowledge_silo_detected(self):
        result = _make_result(cc=10, cogc=25, cov=0.0)
        tags = tornhill_analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "KNOWLEDGE_SILO" in tag_ids


class TestTornhillGitAware:
    """Tests for git-wired Tornhill behavioral analysis."""

    def test_active_hotspot_detected(self):
        result = _make_result(cc=10, cov=0.0)
        ctx = GitContext(change_frequency=15, hotspot_score=15 * 110.0)
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "HOTSPOT_ACTIVE" in tag_ids

    def test_no_hotspot_for_low_churn(self):
        result = _make_result(cc=10, cov=0.0)
        ctx = GitContext(change_frequency=2)
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "HOTSPOT_ACTIVE" not in tag_ids

    def test_deteriorating_trend_detected(self):
        result = _make_result(cc=5, cov=50.0)
        ctx = GitContext(trend="DETERIORATING")
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "TREND_DETERIORATING" in tag_ids

    def test_slowly_degrading_detected(self):
        result = _make_result(cc=5, cov=50.0)
        ctx = GitContext(trend="SLOWLY_DEGRADING")
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "TREND_DEGRADING" in tag_ids

    def test_stable_trend_no_tag(self):
        result = _make_result(cc=5, cov=50.0)
        ctx = GitContext(trend="STABLE")
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "TREND_DETERIORATING" not in tag_ids
        assert "TREND_DEGRADING" not in tag_ids

    def test_knowledge_silo_confirmed(self):
        result = _make_result(cc=8, cov=0.0)
        ctx = GitContext(truck_factor=1, primary_author="Alice", primary_ownership_pct=0.95)
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "KNOWLEDGE_SILO_CONFIRMED" in tag_ids

    def test_no_silo_for_distributed_knowledge(self):
        result = _make_result(cc=8, cov=0.0)
        ctx = GitContext(truck_factor=4, primary_ownership_pct=0.3)
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "KNOWLEDGE_SILO_CONFIRMED" not in tag_ids

    def test_change_coupling_detected(self):
        result = _make_result(cc=5, cov=50.0)
        ctx = GitContext(coupling_count=4)
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "CHANGE_COUPLED" in tag_ids

    def test_churn_hotspot_healthy(self):
        result = _make_result(cc=3, cov=80.0)
        ctx = GitContext(change_frequency=25)
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        assert "CHURN_HOTSPOT" in tag_ids

    def test_includes_static_tags_too(self):
        """Git-aware analysis should include static tags as well."""
        result = _make_result(cc=15, cogc=15, cov=0.0)
        ctx = GitContext(change_frequency=10, hotspot_score=10 * 240.0)
        tags = analyze_with_git(result, ctx)
        tag_ids = [t.tag_id for t in tags]
        # Should have static HOTSPOT_DORMANT AND git HOTSPOT_ACTIVE
        assert "HOTSPOT_DORMANT" in tag_ids
        assert "HOTSPOT_ACTIVE" in tag_ids


class TestFordFitness:
    def test_builtin_fitness_functions_exist(self):
        assert len(BUILTIN_FITNESS_FUNCTIONS) >= 4

    def test_clean_function_passes_all(self):
        result = _make_result(cc=3, cogc=3, cov=100.0)
        tags = ford_analyze(result)
        assert len(tags) == 0

    def test_high_crap_fails_fitness(self):
        result = _make_result(cc=10, cov=0.0)
        tags = ford_analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "FITNESS_CRAP_EXCEEDED" in tag_ids

    def test_high_cogc_fails_fitness(self):
        result = _make_result(cc=3, cogc=20, cov=100.0)
        tags = ford_analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "FITNESS_COGC_EXCEEDED" in tag_ids

    def test_high_abc_fails_fitness(self):
        result = _make_result(cc=3, cov=100.0, abc_scalar=35.0)
        tags = ford_analyze(result)
        tag_ids = [t.tag_id for t in tags]
        assert "FITNESS_ABC_EXCEEDED" in tag_ids

    def test_fitness_tags_have_recommendations(self):
        result = _make_result(cc=10, cov=0.0)
        tags = ford_analyze(result)
        for tag in tags:
            assert len(tag.recommendations) > 0
