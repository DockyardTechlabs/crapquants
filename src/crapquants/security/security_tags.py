"""
Security tag mapping — converts SecurityFinding to DiagnosticTag.

Bridges the security module with the framework tag system so security
findings appear alongside Feathers/Ousterhout/etc. tags in reports.
"""

from __future__ import annotations

from crapquants.frameworks.tags import (
    DiagnosticTag,
    Framework,
    Recommendation,
    Severity,
)
from crapquants.security.ast_security import SecurityFinding


_SEVERITY_MAP = {
    "high": Severity.HIGH,
    "warning": Severity.WARNING,
    "info": Severity.INFO,
}

_RECOMMENDATIONS = {
    "EVAL_USAGE": (
        Recommendation("Replace eval() with ast.literal_eval()", "Safe for literal expressions", 1),
        Recommendation("Use a restricted parser", "If complex expressions needed", 2),
    ),
    "EXEC_USAGE": (
        Recommendation("Eliminate exec()", "Refactor to avoid dynamic code execution", 1),
    ),
    "PICKLE_DESERIALIZE": (
        Recommendation("Use json.loads() or msgpack", "Safe serialization formats", 1),
        Recommendation("If pickle required, validate source", "Only load from trusted, signed sources", 2),
    ),
    "MARSHAL_DESERIALIZE": (
        Recommendation("Use json or msgpack instead", "Marshal is not safe for untrusted data", 1),
    ),
    "SHELL_INJECTION": (
        Recommendation("Use subprocess with shell=False", "Pass args as list, not string", 1),
        Recommendation("Use shlex.quote() if shell=True unavoidable", "Escape user input", 2),
    ),
    "UNSAFE_YAML": (
        Recommendation("Use yaml.safe_load()", "Drop-in replacement, blocks code execution", 1),
    ),
    "HARDCODED_SECRET": (
        Recommendation("Move to environment variable", "Read at runtime only (Rule #21)", 1),
        Recommendation("Use Mozilla SOPS or secrets manager", "Encrypt secrets at rest (Rule #11)", 2),
    ),
}


def finding_to_tag(finding: SecurityFinding) -> DiagnosticTag:
    """
    Convert a SecurityFinding to a DiagnosticTag.

    Args:
        finding: Security finding from AST scan or Semgrep.

    Returns:
        DiagnosticTag compatible with the framework reporting system.
    """
    severity = _SEVERITY_MAP.get(finding.severity, Severity.WARNING)
    tag_id = f"SECURITY_{finding.rule_id}"

    cwe_note = f" ({finding.cwe})" if finding.cwe else ""
    description = f"{finding.message}{cwe_note}"

    recs = _RECOMMENDATIONS.get(finding.rule_id, ())

    return DiagnosticTag(
        tag_id=tag_id,
        framework=Framework.FORD,  # Security is an architectural fitness function
        severity=severity,
        description=description,
        recommendations=recs,
    )


def findings_to_tags(findings: list[SecurityFinding]) -> list[DiagnosticTag]:
    """Convert a list of SecurityFinding to DiagnosticTag list."""
    return [finding_to_tag(f) for f in findings]
