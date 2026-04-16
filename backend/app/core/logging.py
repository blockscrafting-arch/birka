"""Structured logging configuration.

Do not log PII (telegram_id, email, tokens, etc.). Use internal IDs (e.g. user_id) only when needed for audit.
"""

import logging
import sys

import structlog


def configure_logging() -> None:
    """Configure structlog for JSON-like logs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


logger = structlog.get_logger("birka")
