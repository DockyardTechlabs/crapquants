"""
Change coupling detection — files that frequently change together.

Source: Adam Tornhill, Your Code as a Crime Scene (2024)

Coupling types:
    - Intrinsic: Files share a responsibility (legitimate, but consider merging)
    - Incidental: Files coupled due to poor decomposition (refactoring opportunity)
    - Copy-paste: Duplicated code changing in tandem (DRY violation)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from crapquants.git.log_parser import GitCommit


@dataclass(frozen=True)
class CoupledPair:
    """A pair of files that frequently change together."""

    file_a: str
    file_b: str
    shared_commits: int
    total_commits_a: int
    total_commits_b: int
    coupling_ratio: float  # shared / max(a, b)


def detect_change_coupling(
    commits: list[GitCommit],
    min_shared_commits: int = 3,
    min_coupling_ratio: float = 0.3,
    max_files_per_commit: int = 20,
) -> list[CoupledPair]:
    """
    Detect files that frequently change together in the same commits.

    Filters out large commits (merges, renames) that would create
    spurious coupling signals.

    Args:
        commits: Parsed git commits.
        min_shared_commits: Minimum shared commits to report.
        min_coupling_ratio: Minimum coupling ratio to report.
        max_files_per_commit: Ignore commits touching more than this many files.

    Returns:
        List of CoupledPair, sorted by coupling_ratio descending.
    """
    pair_counts: Counter[tuple[str, str]] = Counter()
    file_counts: Counter[str] = Counter()

    for commit in commits:
        files = [f for f in commit.files_changed if f.endswith(".py")]

        # Skip large commits (merges, bulk renames)
        if len(files) > max_files_per_commit:
            continue

        file_counts.update(files)

        # Count co-changes for all pairs
        for pair in combinations(sorted(files), 2):
            pair_counts[pair] += 1

    coupled: list[CoupledPair] = []
    for (a, b), shared in pair_counts.items():
        if shared >= min_shared_commits:
            max_individual = max(file_counts[a], file_counts[b])
            ratio = shared / max_individual if max_individual > 0 else 0.0

            if ratio >= min_coupling_ratio:
                coupled.append(CoupledPair(
                    file_a=a,
                    file_b=b,
                    shared_commits=shared,
                    total_commits_a=file_counts[a],
                    total_commits_b=file_counts[b],
                    coupling_ratio=round(ratio, 3),
                ))

    coupled.sort(key=lambda c: c.coupling_ratio, reverse=True)
    return coupled
