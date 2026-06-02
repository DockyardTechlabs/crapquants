"""
Knowledge analysis — truck factor and knowledge distribution.

Source: Adam Tornhill, Your Code as a Crime Scene (2024)

Truck factor = minimum developers who could leave before
a file/module becomes unmaintainable.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from crapquants.git.log_parser import GitCommit


@dataclass(frozen=True)
class KnowledgeProfile:
    """Knowledge distribution for a single file."""

    file_path: str
    truck_factor: int
    primary_author: str | None
    primary_ownership_pct: float  # 0.0 to 1.0
    total_authors: int
    total_commits: int
    knowledge_risk: str  # "HIGH" | "MEDIUM" | "LOW"


def compute_truck_factor(
    commits: list[GitCommit],
    file_path: str,
    ownership_threshold: float = 0.5,
) -> KnowledgeProfile:
    """
    Compute truck factor for a specific file.

    Truck factor = minimum authors needed to cover
    ownership_threshold (default 50%) of commits.

    Args:
        commits: Parsed git commits.
        file_path: File to analyze.
        ownership_threshold: Fraction of commits to cover (default 0.5).

    Returns:
        KnowledgeProfile for the file.
    """
    author_commits: Counter[str] = Counter()
    for commit in commits:
        if file_path in commit.files_changed:
            author_commits[commit.author] += 1

    total = sum(author_commits.values())
    if total == 0:
        return KnowledgeProfile(
            file_path=file_path,
            truck_factor=0,
            primary_author=None,
            primary_ownership_pct=0.0,
            total_authors=0,
            total_commits=0,
            knowledge_risk="HIGH",
        )

    sorted_authors = sorted(author_commits.items(), key=lambda x: -x[1])
    primary_author = sorted_authors[0][0]
    primary_ownership = sorted_authors[0][1] / total

    # How many authors cover threshold% of commits?
    cumulative = 0
    truck_factor = 0
    for _, count in sorted_authors:
        cumulative += count
        truck_factor += 1
        if cumulative >= total * ownership_threshold:
            break

    knowledge_risk = (
        "HIGH" if truck_factor <= 1
        else "MEDIUM" if truck_factor <= 2
        else "LOW"
    )

    return KnowledgeProfile(
        file_path=file_path,
        truck_factor=truck_factor,
        primary_author=primary_author,
        primary_ownership_pct=round(primary_ownership, 3),
        total_authors=len(author_commits),
        total_commits=total,
        knowledge_risk=knowledge_risk,
    )


def compute_all_truck_factors(
    commits: list[GitCommit],
    file_paths: list[str],
) -> list[KnowledgeProfile]:
    """
    Compute truck factor for multiple files.

    Args:
        commits: Parsed git commits.
        file_paths: Files to analyze.

    Returns:
        List of KnowledgeProfile, sorted by truck_factor ascending (riskiest first).
    """
    profiles = [
        compute_truck_factor(commits, fp)
        for fp in file_paths
    ]
    profiles.sort(key=lambda p: p.truck_factor)
    return profiles
