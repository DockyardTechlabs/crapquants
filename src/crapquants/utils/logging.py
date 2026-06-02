"""
Structured logging configuration for CRAPQuants.

Uses structlog with JSON output for machine-parseable logs.
Console output uses rich for human-readable formatting.
"""

from __future__ import annotations

import structlog


def configure_logging(json_output: bool = False, log_level: str = "INFO") -> None:
    """
    Configure structlog for CRAPQuants.

    Args:
        json_output: If True, output JSON lines (for CI/files).
                     If False, output rich console format (for interactive use).
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
