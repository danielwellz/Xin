"""Tracing helper utilities."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import TypedDict, cast
from uuid import uuid4

from opentelemetry.trace import INVALID_SPAN, Span, SpanContext, get_current_span


class TraceContext(TypedDict, total=False):
    trace_id: str
    span_id: str


def generate_trace_id() -> str:
    """Generate a random UUID-based trace identifier."""

    return uuid4().hex


def _format_span_ids(span: Span) -> TraceContext:
    context: MutableMapping[str, str] = {}

    span_context: SpanContext = span.get_span_context()
    if span_context == INVALID_SPAN.get_span_context() or not span_context.is_valid:
        return cast(TraceContext, {})

    context["trace_id"] = f"{span_context.trace_id:032x}"
    context["span_id"] = f"{span_context.span_id:016x}"
    return cast(TraceContext, context)


def get_current_trace_ids() -> TraceContext:
    """Return the active trace/span identifiers if present."""

    span = get_current_span()
    return _format_span_ids(span)


@dataclass(slots=True)
class UUIDTraceIdGenerator:
    """Simple generator that can be used by logging or request middleware."""

    def __call__(self) -> str:
        return generate_trace_id()
