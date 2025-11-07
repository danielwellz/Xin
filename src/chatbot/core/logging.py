"""Structlog configuration helpers with OpenTelemetry enrichment."""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

from chatbot.utils.tracing import TraceContext, get_current_trace_ids

_CONFIGURED = False


def _otel_enricher(
    _: Any,
    __: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Inject OpenTelemetry trace identifiers into the log event if available."""

    trace_context: TraceContext = get_current_trace_ids()
    if trace_context.get("trace_id"):
        event_dict.setdefault("trace_id", trace_context["trace_id"])
    if trace_context.get("span_id"):
        event_dict.setdefault("span_id", trace_context["span_id"])
    return event_dict


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog with JSON output and OTEL context."""

    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.basicConfig(format="%(message)s", level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            _otel_enricher,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to the provided name."""

    configure_logging()
    if name is None:
        return structlog.get_logger()
    return structlog.get_logger(name)
