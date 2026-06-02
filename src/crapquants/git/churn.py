"""
Churn analysis — change frequency per file for hotspot detection.

Source: Adam Tornhill, Your Code as a Crime Scene (2024)

Hotspot formula: hotspot_score = change_frequency × complexity
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from crapquants.git.log_parser import GitCommit


@dataclass(frozen=True)
class FileChurn:
    """Change frequency data for a single file."""

    file_path: str
    commit_count: int
    total_insertions: int
    total_deletions: int
    churn: int  # insertions + deletions
    unique_authors: int
    last_modified: datetime | None


@dataclass(frozen=True)
class Hotspot:
    """A hotspot — file with high churn AND high complexity."""

    file_path: str
    commit_count: int
    crap_score: float
    hotspot_score: float  # commit_count × crap_score


def compute_file_churn(
    commits: list[GitCommit],
    analysis_window_days: int = 365,
) -> list[FileChurn]:
    """
    Compute change frequency for each file from git history.

    Args:
        commits: Parsed git commits.
        analysis_window_days: Only count commits within this window.

    Returns:
        List of FileChurn, sorted by commit_count descending.
    """
    cutoff = datetime.now().astimezone() - timedelta(days=analysis_window_days)

    commit_counts: Counter[str] = Counter()
    insertions: Counter[str] = Counter()
    deletions_count: Counter[str] = Counter()
    authors: dict[str, set[str]] = {}
    last_modified: dict[str, datetime] = {}

    for commit in commits:
        if commit.date.astimezone() < cutoff:
            continue

        for fp in commit.files_changed:
            commit_counts[fp] += 1
            insertions[fp] += commit.insertions.get(fp, 0)
            deletions_count[fp] += commit.deletions.get(fp, 0)

            if fp not in authors:
                authors[fp] = set()
            authors[fp].add(commit.author)

            if fp not in last_modified or commit.date > last_modified[fp]:
                last_modified[fp] = commit.date

    results = []
    for fp, count in commit_counts.most_common():
        results.append(FileChurn(
            file_path=fp,
            commit_count=count,
            total_insertions=insertions[fp],
            total_deletions=deletions_count[fp],
            churn=insertions[fp] + deletions_count[fp],
            unique_authors=len(authors.get(fp, set())),
            last_modified=last_modified.get(fp),
        ))

    return results


def compute_hotspots(
    churn_data: list[FileChurn],
    crap_scores: dict[str, float],
    top_n: int = 20,
) -> list[Hotspot]:
    """
    Compute hotspots by intersecting churn with CRAP scores.

    Hotspot score = commit_count × max_crap_score_in_file

    Args:
        churn_data: File churn data from git history.
        crap_scores: Dict mapping file_path to max CRAP score in that file.
        top_n: Return top N hotspots.

    Returns:
        List of Hotspot, sorted by hotspot_score descending.
    """
    hotspots = []
    for churn in churn_data:
        crap = crap_scores.get(churn.file_path, 0.0)
        if crap > 0 and churn.commit_count > 0:
            hotspots.append(Hotspot(
                file_path=churn.file_path,
                commit_count=churn.commit_count,
                crap_score=crap,
                hotspot_score=round(churn.commit_count * crap, 2),
            ))

    hotspots.sort(key=lambda h: h.hotspot_score, reverse=True)
    return hotspots[:top_n]
