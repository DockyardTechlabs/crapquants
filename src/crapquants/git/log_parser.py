"""
Git log parser — extracts commit history for behavioral code analysis.

Parses `git log --numstat --format=...` output to produce structured
commit data for hotspot detection, change coupling, and truck factor.

No git library dependency — pure subprocess + text parsing.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GitCommit:
    """A single parsed git commit."""

    hash: str
    author: str
    date: datetime
    message: str
    files_changed: tuple[str, ...]
    insertions: dict[str, int] = field(default_factory=dict)
    deletions: dict[str, int] = field(default_factory=dict)


def parse_git_log(
    repo_path: str | Path = ".",
    max_commits: int = 1000,
    since_days: int = 365,
    file_filter: str = "*.py",
) -> list[GitCommit]:
    """
    Parse git log for a repository.

    Runs: git log --numstat --format="COMMIT_SEP%n%H%n%an%n%aI%n%s"
    Then parses the output into GitCommit objects.

    Args:
        repo_path: Path to git repository root.
        max_commits: Maximum commits to parse.
        since_days: Only include commits from last N days.
        file_filter: Only include files matching this pattern.

    Returns:
        List of GitCommit objects, newest first.

    Raises:
        FileNotFoundError: If repo_path doesn't exist.
        RuntimeError: If git command fails.
    """
    repo_path = Path(repo_path)
    if not (repo_path / ".git").exists() and not repo_path.name == ".git":
        raise FileNotFoundError(f"Not a git repository: {repo_path}")

    cmd = [
        "git", "-C", str(repo_path),
        "log",
        f"--max-count={max_commits}",
        f"--since={since_days} days ago",
        "--numstat",
        "--format=COMMIT_SEP%n%H%n%an%n%aI%n%s",
        "--", file_filter,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        logger.error("git_log_timeout", repo=str(repo_path))
        raise RuntimeError("git log timed out after 60 seconds")
    except FileNotFoundError:
        raise RuntimeError("git command not found — is git installed?")

    if result.returncode != 0:
        logger.error("git_log_failed", stderr=result.stderr[:200])
        raise RuntimeError(f"git log failed: {result.stderr[:200]}")

    return _parse_log_output(result.stdout)


def _parse_log_output(output: str) -> list[GitCommit]:
    """Parse raw git log output into GitCommit objects."""
    commits: list[GitCommit] = []

    blocks = output.split("COMMIT_SEP\n")
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        if len(lines) < 4:
            continue

        commit_hash = lines[0].strip()
        author = lines[1].strip()
        date_str = lines[2].strip()
        message = lines[3].strip()

        try:
            date = datetime.fromisoformat(date_str)
        except ValueError:
            continue

        files: list[str] = []
        insertions: dict[str, int] = {}
        deletions: dict[str, int] = {}

        for stat_line in lines[4:]:
            stat_line = stat_line.strip()
            if not stat_line:
                continue
            parts = stat_line.split("\t")
            if len(parts) == 3:
                ins, dels, filepath = parts
                filepath = filepath.strip()
                if filepath:
                    files.append(filepath)
                    try:
                        insertions[filepath] = int(ins) if ins != "-" else 0
                        deletions[filepath] = int(dels) if dels != "-" else 0
                    except ValueError:
                        pass

        if commit_hash and files:
            commits.append(GitCommit(
                hash=commit_hash,
                author=author,
                date=date,
                message=message,
                files_changed=tuple(files),
                insertions=insertions,
                deletions=deletions,
            ))

    logger.info("git_log_parsed", commits=len(commits))
    return commits


def get_current_commit(repo_path: str | Path = ".") -> str | None:
    """Get current HEAD commit hash."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None
