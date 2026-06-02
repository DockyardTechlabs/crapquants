"""Tests for git analysis modules — churn, coupling, knowledge, trends."""

from datetime import datetime, timezone, timedelta

import pytest

from crapquants.git.log_parser import GitCommit, _parse_log_output
from crapquants.git.churn import compute_file_churn, compute_hotspots, FileChurn
from crapquants.git.coupling import detect_change_coupling
from crapquants.git.knowledge import compute_truck_factor, compute_all_truck_factors
from crapquants.git.trends import classify_trend, compute_trend, _linear_slope


# ---------------------------------------------------------------------------
# Fixtures — synthetic git commits
# ---------------------------------------------------------------------------

def _commit(hash: str, author: str, days_ago: int, files: list[str],
            message: str = "fix") -> GitCommit:
    """Helper to create a test commit."""
    date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return GitCommit(
        hash=hash, author=author, date=date, message=message,
        files_changed=tuple(files),
        insertions={f: 10 for f in files},
        deletions={f: 5 for f in files},
    )


@pytest.fixture
def sample_commits() -> list[GitCommit]:
    """Realistic commit history for testing."""
    return [
        _commit("aaa", "Alice", 1, ["src/core.py", "src/utils.py"]),
        _commit("bbb", "Alice", 3, ["src/core.py"]),
        _commit("ccc", "Bob", 5, ["src/core.py", "src/api.py"]),
        _commit("ddd", "Alice", 10, ["src/core.py", "src/utils.py"]),
        _commit("eee", "Charlie", 15, ["src/api.py"]),
        _commit("fff", "Alice", 20, ["src/core.py"]),
        _commit("ggg", "Bob", 30, ["src/core.py", "src/api.py", "src/utils.py"]),
        _commit("hhh", "Alice", 45, ["src/core.py"]),
        _commit("iii", "Alice", 60, ["src/standalone.py"]),
    ]


# ---------------------------------------------------------------------------
# Log parser tests
# ---------------------------------------------------------------------------

class TestLogParser:
    def test_parse_log_output(self):
        raw = (
            "COMMIT_SEP\n"
            "abc123\n"
            "Alice\n"
            "2024-06-15T10:30:00+00:00\n"
            "Fix bug in parser\n"
            "10\t5\tsrc/parser.py\n"
            "3\t1\tsrc/utils.py\n"
        )
        commits = _parse_log_output(raw)
        assert len(commits) == 1
        assert commits[0].hash == "abc123"
        assert commits[0].author == "Alice"
        assert len(commits[0].files_changed) == 2
        assert commits[0].insertions["src/parser.py"] == 10

    def test_parse_multiple_commits(self):
        raw = (
            "COMMIT_SEP\n"
            "aaa\nAlice\n2024-06-15T10:00:00+00:00\nFirst\n"
            "5\t2\tfile_a.py\n"
            "\n"
            "COMMIT_SEP\n"
            "bbb\nBob\n2024-06-14T10:00:00+00:00\nSecond\n"
            "3\t1\tfile_b.py\n"
        )
        commits = _parse_log_output(raw)
        assert len(commits) == 2

    def test_parse_empty_output(self):
        assert _parse_log_output("") == []

    def test_parse_malformed_skipped(self):
        raw = "COMMIT_SEP\nonly_one_line\n"
        commits = _parse_log_output(raw)
        assert len(commits) == 0


# ---------------------------------------------------------------------------
# Churn tests
# ---------------------------------------------------------------------------

class TestChurn:
    def test_file_churn_counts(self, sample_commits):
        churn = compute_file_churn(sample_commits)
        core = [c for c in churn if c.file_path == "src/core.py"][0]
        assert core.commit_count == 7  # Touched in 7 commits

    def test_churn_sorted_by_count(self, sample_commits):
        churn = compute_file_churn(sample_commits)
        counts = [c.commit_count for c in churn]
        assert counts == sorted(counts, reverse=True)

    def test_unique_authors(self, sample_commits):
        churn = compute_file_churn(sample_commits)
        core = [c for c in churn if c.file_path == "src/core.py"][0]
        # core.py touched by: Alice(aaa,bbb,ddd,fff,hhh), Bob(ccc,ggg) = 2 authors
        assert core.unique_authors == 2

    def test_hotspot_calculation(self, sample_commits):
        churn = compute_file_churn(sample_commits)
        crap_scores = {"src/core.py": 45.0, "src/api.py": 20.0}
        hotspots = compute_hotspots(churn, crap_scores)
        assert len(hotspots) >= 1
        # core.py should be #1 (7 commits × 45.0 CRAP)
        assert hotspots[0].file_path == "src/core.py"
        assert hotspots[0].hotspot_score == 7 * 45.0

    def test_hotspot_empty_crap(self, sample_commits):
        churn = compute_file_churn(sample_commits)
        hotspots = compute_hotspots(churn, {})
        assert len(hotspots) == 0


# ---------------------------------------------------------------------------
# Change coupling tests
# ---------------------------------------------------------------------------

class TestChangeCoupling:
    def test_detects_coupled_files(self, sample_commits):
        coupled = detect_change_coupling(
            sample_commits, min_shared_commits=2, min_coupling_ratio=0.2,
        )
        # core.py + utils.py change together in commits aaa, ddd, ggg = 3 times
        pairs = [(c.file_a, c.file_b) for c in coupled]
        assert any("core.py" in a and "utils.py" in b for a, b in pairs)

    def test_coupling_ratio_correct(self, sample_commits):
        coupled = detect_change_coupling(
            sample_commits, min_shared_commits=2, min_coupling_ratio=0.0,
        )
        for cp in coupled:
            expected = cp.shared_commits / max(cp.total_commits_a, cp.total_commits_b)
            assert abs(cp.coupling_ratio - round(expected, 3)) < 0.01

    def test_min_shared_filters(self, sample_commits):
        coupled = detect_change_coupling(sample_commits, min_shared_commits=100)
        assert len(coupled) == 0

    def test_large_commits_filtered(self):
        # One commit touches 50 files — should be filtered
        big_commit = _commit("big", "Alice", 1, [f"src/f{i}.py" for i in range(50)])
        coupled = detect_change_coupling([big_commit], max_files_per_commit=20)
        assert len(coupled) == 0


# ---------------------------------------------------------------------------
# Knowledge / Truck factor tests
# ---------------------------------------------------------------------------

class TestKnowledge:
    def test_truck_factor_single_author(self):
        commits = [
            _commit("a", "Alice", 1, ["src/solo.py"]),
            _commit("b", "Alice", 2, ["src/solo.py"]),
            _commit("c", "Alice", 3, ["src/solo.py"]),
        ]
        profile = compute_truck_factor(commits, "src/solo.py")
        assert profile.truck_factor == 1
        assert profile.primary_author == "Alice"
        assert profile.primary_ownership_pct == 1.0
        assert profile.knowledge_risk == "HIGH"

    def test_truck_factor_distributed(self):
        commits = [
            _commit("a", "Alice", 1, ["src/shared.py"]),
            _commit("b", "Bob", 2, ["src/shared.py"]),
            _commit("c", "Charlie", 3, ["src/shared.py"]),
            _commit("d", "Diana", 4, ["src/shared.py"]),
        ]
        profile = compute_truck_factor(commits, "src/shared.py")
        assert profile.truck_factor >= 2
        assert profile.total_authors == 4
        assert profile.knowledge_risk in ("MEDIUM", "LOW")

    def test_truck_factor_no_commits(self):
        profile = compute_truck_factor([], "src/missing.py")
        assert profile.truck_factor == 0
        assert profile.knowledge_risk == "HIGH"

    def test_all_truck_factors(self, sample_commits):
        profiles = compute_all_truck_factors(
            sample_commits, ["src/core.py", "src/standalone.py"],
        )
        assert len(profiles) == 2
        # Both have truck_factor=1, sorted ascending by tf
        # Both HIGH risk since each has a dominant single author
        assert all(p.knowledge_risk == "HIGH" for p in profiles)


# ---------------------------------------------------------------------------
# Trend tests
# ---------------------------------------------------------------------------

class TestTrends:
    def test_stable_trend(self):
        assert classify_trend([10.0, 10.1, 10.0, 9.9, 10.0]) == "STABLE"

    def test_deteriorating_trend(self):
        assert classify_trend([5.0, 10.0, 20.0, 35.0, 50.0]) == "DETERIORATING"

    def test_improving_trend(self):
        assert classify_trend([50.0, 35.0, 20.0, 10.0, 5.0]) == "IMPROVING"

    def test_slowly_degrading(self):
        # Slope ~1.0 per step should trigger SLOWLY_DEGRADING (>0.5)
        assert classify_trend([10.0, 11.0, 12.0, 13.0, 14.0]) == "SLOWLY_DEGRADING"

    def test_slowly_improving(self):
        assert classify_trend([14.0, 13.0, 12.0, 11.0, 10.0]) == "SLOWLY_IMPROVING"

    def test_insufficient_data(self):
        assert classify_trend([10.0, 20.0]) == "INSUFFICIENT_DATA"

    def test_compute_trend_result(self):
        result = compute_trend("file.py", [5.0, 10.0, 20.0, 35.0, 50.0])
        assert result.trend == "DETERIORATING"
        assert result.slope > 0
        assert result.earliest_crap == 5.0
        assert result.latest_crap == 50.0

    def test_compute_trend_empty(self):
        result = compute_trend("file.py", [])
        assert result.trend == "INSUFFICIENT_DATA"
        assert result.data_points == 0

    def test_linear_slope_flat(self):
        assert _linear_slope([10.0, 10.0, 10.0]) == 0.0

    def test_linear_slope_positive(self):
        assert _linear_slope([0.0, 1.0, 2.0, 3.0]) == 1.0

    def test_linear_slope_negative(self):
        assert _linear_slope([3.0, 2.0, 1.0, 0.0]) == -1.0
