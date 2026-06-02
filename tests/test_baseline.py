"""Tests for baseline save and compare modules."""

import json
from pathlib import Path

import pytest

from crapquants.core.complexity import FunctionMetrics
from crapquants.core.crap import CRAPResult, calculate_crap
from crapquants.core.merge import MergedFileResult, MergedFunctionResult
from crapquants.baseline.save import save_baseline
from crapquants.baseline.compare import compare, load_baseline, ComparisonResult


def _make_func(name="func", cc=5, cov=50.0, file_path="src/mod.py"):
    crap_score = calculate_crap(cc, cov)
    return MergedFunctionResult(
        metrics=FunctionMetrics(
            name=name, file_path=file_path, line_start=1, line_end=20,
            cyclomatic_complexity=cc, cognitive_complexity=cc,
            abc_assignments=3, abc_branches=5, abc_conditions=3,
            abc_scalar=7.0, line_count=20,
            max_nesting_depth=2, parameter_count=2,
        ),
        coverage=None,
        crap=CRAPResult(
            function_name=name, file_path=file_path, line_number=1,
            complexity=cc, coverage=cov, crap_score=crap_score,
            crapload=0, is_crappy=crap_score > 30,
            min_coverage_needed=0.0, complexity_threshold_exceeded=cc >= 31,
        ),
    )


def _make_file_result(functions, file_path="src/mod.py"):
    return MergedFileResult(
        file_path=file_path,
        file_metrics=type('FM', (), {
            'halstead_volume': 0, 'halstead_difficulty': 0,
            'halstead_effort': 0, 'maintainability_index': 0,
            'total_lines': 50, 'code_lines': 40,
            'comment_lines': 5, 'blank_lines': 5,
        })(),
        file_coverage=None,
        functions=functions,
    )


class TestSaveBaseline:
    def test_saves_file(self, tmp_path):
        results = [_make_file_result([_make_func("f1"), _make_func("f2")])]
        path = save_baseline(results, tmp_path / "baseline.json")
        assert Path(path).exists()

    def test_baseline_structure(self, tmp_path):
        results = [_make_file_result([_make_func("f1", cc=3, cov=100.0)])]
        save_baseline(results, tmp_path / "baseline.json")
        data = json.loads((tmp_path / "baseline.json").read_text())
        assert data["schema_version"] == "1.0.0"
        assert data["total_functions"] == 1
        assert len(data["entries"]) == 1
        assert "chain_hash" in data["entries"][0]
        assert "chain_head" in data

    def test_hash_chaining(self, tmp_path):
        results = [_make_file_result([_make_func("f1"), _make_func("f2"), _make_func("f3")])]
        save_baseline(results, tmp_path / "baseline.json")
        data = json.loads((tmp_path / "baseline.json").read_text())
        hashes = [e["chain_hash"] for e in data["entries"]]
        # All hashes unique
        assert len(set(hashes)) == 3
        # Last hash equals chain_head
        assert data["chain_head"] == hashes[-1]

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "baseline.json"
        results = [_make_file_result([_make_func("f1")])]
        save_baseline(results, path)
        assert path.exists()

    def test_git_commit_stored(self, tmp_path):
        results = [_make_file_result([_make_func("f1")])]
        save_baseline(results, tmp_path / "baseline.json", git_commit="abc123")
        data = json.loads((tmp_path / "baseline.json").read_text())
        assert data["git_commit"] == "abc123"


class TestLoadBaseline:
    def test_loads_valid_baseline(self, tmp_path):
        results = [_make_file_result([_make_func("f1")])]
        save_baseline(results, tmp_path / "baseline.json")
        data = load_baseline(tmp_path / "baseline.json")
        assert data["total_functions"] == 1

    def test_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_baseline("/nonexistent/baseline.json")

    def test_invalid_format_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text('{"no_entries": true}')
        with pytest.raises(ValueError, match="Invalid baseline"):
            load_baseline(bad)


class TestCompare:
    def test_no_changes(self, tmp_path):
        funcs = [_make_func("f1", cc=5, cov=50.0)]
        results = [_make_file_result(funcs)]
        save_baseline(results, tmp_path / "baseline.json")
        comp = compare(results, tmp_path / "baseline.json")
        assert not comp.is_regression
        assert len(comp.new_crappy) == 0
        assert len(comp.worsened) == 0

    def test_new_crappy_detected(self, tmp_path):
        # Baseline: clean function
        clean = [_make_func("f1", cc=3, cov=100.0)]
        save_baseline([_make_file_result(clean)], tmp_path / "baseline.json")
        # Current: same function now CRAPpy
        crappy = [_make_func("f1", cc=15, cov=0.0)]
        comp = compare([_make_file_result(crappy)], tmp_path / "baseline.json")
        assert comp.is_regression
        assert len(comp.new_crappy) == 1
        assert comp.new_crappy[0].function == "f1"

    def test_fixed_function_detected(self, tmp_path):
        # Baseline: CRAPpy
        crappy = [_make_func("f1", cc=15, cov=0.0)]
        save_baseline([_make_file_result(crappy)], tmp_path / "baseline.json")
        # Current: fixed
        clean = [_make_func("f1", cc=3, cov=100.0)]
        comp = compare([_make_file_result(clean)], tmp_path / "baseline.json")
        assert not comp.is_regression
        assert len(comp.fixed) == 1

    def test_worsened_detected(self, tmp_path):
        # Baseline: moderate
        before = [_make_func("f1", cc=5, cov=50.0)]
        save_baseline([_make_file_result(before)], tmp_path / "baseline.json")
        # Current: worse (higher CC, same coverage)
        after = [_make_func("f1", cc=8, cov=50.0)]
        comp = compare([_make_file_result(after)], tmp_path / "baseline.json")
        assert len(comp.worsened) == 1

    def test_improved_detected(self, tmp_path):
        before = [_make_func("f1", cc=8, cov=50.0)]
        save_baseline([_make_file_result(before)], tmp_path / "baseline.json")
        after = [_make_func("f1", cc=3, cov=50.0)]
        comp = compare([_make_file_result(after)], tmp_path / "baseline.json")
        assert len(comp.improved) == 1

    def test_new_function_detected(self, tmp_path):
        before = [_make_func("f1")]
        save_baseline([_make_file_result(before)], tmp_path / "baseline.json")
        after = [_make_func("f1"), _make_func("f2_new")]
        comp = compare([_make_file_result(after)], tmp_path / "baseline.json")
        assert len(comp.new_functions) == 1
        assert comp.new_functions[0].function == "f2_new"

    def test_removed_function_detected(self, tmp_path):
        before = [_make_func("f1"), _make_func("f2")]
        save_baseline([_make_file_result(before)], tmp_path / "baseline.json")
        after = [_make_func("f1")]
        comp = compare([_make_file_result(after)], tmp_path / "baseline.json")
        assert len(comp.removed_functions) == 1
        assert comp.removed_functions[0].function == "f2"

    def test_aggregate_delta(self, tmp_path):
        before = [_make_func("f1", cc=5, cov=50.0)]
        save_baseline([_make_file_result(before)], tmp_path / "baseline.json")
        after = [_make_func("f1", cc=10, cov=50.0)]
        comp = compare([_make_file_result(after)], tmp_path / "baseline.json")
        assert comp.aggregate_delta > 0

    def test_summary_string(self, tmp_path):
        before = [_make_func("f1", cc=3, cov=100.0)]
        save_baseline([_make_file_result(before)], tmp_path / "baseline.json")
        after = [_make_func("f1", cc=15, cov=0.0)]
        comp = compare([_make_file_result(after)], tmp_path / "baseline.json")
        summary = comp.summary
        assert "REGRESSION" in summary
        assert "new CRAPpy" in summary

    def test_baseline_not_found_raises(self):
        results = [_make_file_result([_make_func("f1")])]
        with pytest.raises(FileNotFoundError):
            compare(results, "/nonexistent/baseline.json")
