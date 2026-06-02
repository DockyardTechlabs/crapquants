"""
Semgrep integration — Tier 2 SAST (optional, Level 4).

Invokes Semgrep CLI via subprocess and parses JSON output.
Falls back gracefully if Semgrep is not installed.

Semgrep is NOT a Python dependency — it's a system-level tool.
CRAPQuants only invokes it via subprocess and consumes its JSON output.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import structlog

from crapquants.security.ast_security import SecurityFinding

logger = structlog.get_logger(__name__)


def is_semgrep_available() -> bool:
    """Check if semgrep CLI is installed and accessible."""
    return shutil.which("semgrep") is not None


def run_semgrep(
    target_path: str | Path,
    config: str = "auto",
    timeout: int = 120,
) -> list[SecurityFinding]:
    """
    Run Semgrep SAST scan and return findings as SecurityFinding objects.

    Args:
        target_path: Directory or file to scan.
        config: Semgrep config (e.g., "auto", "p/python", or path to rules).
        timeout: Maximum seconds to wait for Semgrep.

    Returns:
        List of SecurityFinding from Semgrep results.
        Empty list if Semgrep is not installed or fails.
    """
    if not is_semgrep_available():
        logger.info("semgrep_not_installed",
                     message="Semgrep not found. Install with: pip install semgrep")
        return []

    cmd = [
        "semgrep",
        "--config", config,
        "--json",
        "--quiet",
        "--no-git-ignore",
        str(target_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logger.error("semgrep_timeout", timeout=timeout)
        return []
    except FileNotFoundError:
        logger.error("semgrep_not_found")
        return []

    if result.returncode not in (0, 1):
        # Semgrep returns 1 when findings exist, 0 when clean
        logger.warning("semgrep_error", stderr=result.stderr[:300])
        return []

    return _parse_semgrep_json(result.stdout)


def _parse_semgrep_json(json_output: str) -> list[SecurityFinding]:
    """Parse Semgrep JSON output into SecurityFinding objects."""
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        logger.warning("semgrep_json_parse_failed")
        return []

    findings: list[SecurityFinding] = []

    for result in data.get("results", []):
        rule_id = result.get("check_id", "unknown")
        path = result.get("path", "")
        start = result.get("start", {})
        end = result.get("end", {})
        extra = result.get("extra", {})
        severity = extra.get("severity", "WARNING").lower()
        message = extra.get("message", rule_id)

        # Map Semgrep severity to our severity levels
        sev_map = {"error": "high", "warning": "warning", "info": "info"}
        mapped_severity = sev_map.get(severity, "warning")

        # Extract CWE if present in metadata
        metadata = extra.get("metadata", {})
        cwe_list = metadata.get("cwe", [])
        cwe = cwe_list[0] if cwe_list else None

        findings.append(SecurityFinding(
            rule_id=f"SEMGREP_{rule_id.replace('.', '_').upper()}",
            file_path=path,
            line=start.get("line", 0),
            end_line=end.get("line", start.get("line", 0)),
            severity=mapped_severity,
            message=message,
            cwe=cwe,
        ))

    logger.info("semgrep_parsed", findings=len(findings))
    return findings
