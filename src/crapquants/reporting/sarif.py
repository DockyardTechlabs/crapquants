"""
SARIF 2.1.0 report generator for CRAPQuants.

Static Analysis Results Interchange Format — enables integration with
GitHub Code Scanning, Azure DevOps, and other SARIF-consuming tools.

Spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

from __future__ import annotations

import json
from typing import Any

from crapquants.core.merge import MergedFileResult
from crapquants.frameworks.tags import DiagnosticTag, Severity


def _severity_to_sarif_level(severity: Severity) -> str:
    """Map CRAPQuants severity to SARIF level."""
    return {
        Severity.INFO: "note",
        Severity.WARNING: "warning",
        Severity.HIGH: "error",
        Severity.CRITICAL: "error",
    }.get(severity, "warning")


def generate_sarif_report(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
) -> dict[str, Any]:
    """
    Generate SARIF 2.1.0 compliant report.

    Args:
        results: List of merged file results.
        all_tags: Dict mapping "file:func" to diagnostic tags.

    Returns:
        Dict suitable for json.dumps() conforming to SARIF 2.1.0.
    """
    # Collect unique rule definitions from all tags
    rules_map: dict[str, dict[str, Any]] = {}
    sarif_results: list[dict[str, Any]] = []

    for file_result in results:
        for func in file_result.functions:
            m = func.metrics
            c = func.crap
            tag_key = f"{file_result.file_path}:{m.name}"
            func_tags = all_tags.get(tag_key, [])

            # Always add CRAP threshold violation as a result
            if c.is_crappy:
                rule_id = "crapquants/crap-threshold"
                if rule_id not in rules_map:
                    rules_map[rule_id] = {
                        "id": rule_id,
                        "name": "CRAPThresholdExceeded",
                        "shortDescription": {
                            "text": "Function exceeds CRAP score threshold of 30"
                        },
                        "fullDescription": {
                            "text": (
                                "The CRAP (Change Risk Anti-Patterns) score measures "
                                "the interaction between cyclomatic complexity and code "
                                "coverage. A score above 30 indicates high maintenance risk."
                            )
                        },
                        "helpUri": "https://github.com/dockyardtechlabs/crapquants",
                        "defaultConfiguration": {"level": "warning"},
                    }

                sarif_results.append({
                    "ruleId": rule_id,
                    "level": "warning",
                    "message": {
                        "text": (
                            f"CRAP score {c.crap_score:.1f} exceeds threshold 30. "
                            f"CC={m.cyclomatic_complexity}, Coverage={c.coverage:.0f}%. "
                            f"Minimum coverage needed: {c.min_coverage_needed:.0f}%."
                        )
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": file_result.file_path},
                                "region": {
                                    "startLine": m.line_start,
                                    "endLine": m.line_end,
                                },
                            }
                        }
                    ],
                    "properties": {
                        "crap_score": c.crap_score,
                        "coverage": c.coverage,
                        "cyclomatic_complexity": m.cyclomatic_complexity,
                    },
                })

            # Add framework diagnostic tags as SARIF results
            for tag in func_tags:
                rule_id = f"crapquants/{tag.framework.value.lower()}/{tag.tag_id.lower()}"

                if rule_id not in rules_map:
                    rules_map[rule_id] = {
                        "id": rule_id,
                        "name": tag.tag_id,
                        "shortDescription": {"text": tag.description[:200]},
                        "helpUri": "https://github.com/dockyardtechlabs/crapquants",
                        "defaultConfiguration": {
                            "level": _severity_to_sarif_level(tag.severity)
                        },
                        "properties": {"framework": tag.framework.value},
                    }

                result_entry: dict[str, Any] = {
                    "ruleId": rule_id,
                    "level": _severity_to_sarif_level(tag.severity),
                    "message": {"text": tag.description},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": file_result.file_path},
                                "region": {
                                    "startLine": m.line_start,
                                    "endLine": m.line_end,
                                },
                            }
                        }
                    ],
                }

                if tag.recommendations:
                    result_entry["fixes"] = [
                        {
                            "description": {
                                "text": f"{r.action}: {r.rationale}"
                            }
                        }
                        for r in tag.recommendations[:3]
                    ]

                sarif_results.append(result_entry)

    sarif: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "CRAPQuants",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/dockyardtechlabs/crapquants",
                        "shortDescription": {
                            "text": "Python-native CRAP metric tool with book-integrated diagnostics"
                        },
                        "fullDescription": {
                            "text": (
                                "CRAPQuants computes CRAP (Change Risk Anti-Patterns) scores "
                                "by combining cyclomatic complexity with test coverage. "
                                "Formula: CC² × (1 − coverage/100)³ + CC. "
                                "Score > 30 indicates high maintenance risk. "
                                "Enriched with diagnostic tags from six software engineering books."
                            )
                        },
                        "rules": list(rules_map.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }

    return sarif


def write_sarif_report(
    results: list[MergedFileResult],
    all_tags: dict[str, list[DiagnosticTag]],
    output_path: str,
) -> str:
    """Generate and write SARIF report to file."""
    sarif = generate_sarif_report(results, all_tags)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sarif, f, indent=2, ensure_ascii=False)
    return output_path
