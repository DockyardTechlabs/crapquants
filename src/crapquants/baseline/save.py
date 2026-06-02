"""
Baseline save — snapshots current CRAP scores for regression detection.

Saves a compact JSON file with per-function CRAP scores, CC, coverage,
and a hash-chained integrity marker (Rule #24).

Usage:
    crapquants baseline save --output data/baseline.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from crapquants.core.merge import MergedFileResult

logger = structlog.get_logger(__name__)


@staticmethod
def _hash_entry(entry: dict[str, Any], prev_hash: str) -> str:
    """Hash-chain an entry with the previous hash (Rule #24)."""
    payload = json.dumps(entry, sort_keys=True) + prev_hash
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def save_baseline(
    results: list[MergedFileResult],
    output_path: str | Path,
    git_commit: str | None = None,
) -> str:
    """
    Save current CRAP scores as a baseline file.

    The baseline is a compact JSON with per-function entries:
        {file, function, line, cc, coverage, crap_score}

    Includes hash chaining for tamper evidence (Rule #24).

    Args:
        results: Current merged analysis results.
        output_path: Path to write baseline JSON.
        git_commit: Current git commit hash if available.

    Returns:
        Path to saved baseline file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    prev_hash = "genesis"

    for file_result in results:
        for func in file_result.functions:
            m = func.metrics
            c = func.crap

            entry = {
                "file": file_result.file_path,
                "function": m.name,
                "line": m.line_start,
                "cc": m.cyclomatic_complexity,
                "cogc": m.cognitive_complexity,
                "coverage": c.coverage,
                "crap_score": c.crap_score,
                "is_crappy": c.is_crappy,
            }

            entry_hash = _hash_entry(entry, prev_hash)
            entry["chain_hash"] = entry_hash
            prev_hash = entry_hash

            entries.append(entry)

    baseline = {
        "schema_version": "1.0.0",
        "tool": "crapquants",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "total_functions": len(entries),
        "crappy_functions": sum(1 for e in entries if e["is_crappy"]),
        "aggregate_crap": round(sum(e["crap_score"] for e in entries), 2),
        "chain_head": prev_hash,
        "entries": entries,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    logger.info(
        "baseline_saved",
        path=str(output_path),
        functions=len(entries),
        aggregate_crap=baseline["aggregate_crap"],
    )

    return str(output_path)
