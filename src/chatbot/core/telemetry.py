"""Telemetry utilities for tracing and metrics instrumentation."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_TRACING_INITIALISED = False
_HTTPX_INSTRUMENTED = False


def init_tracing(
    service_name: str, *, endpoint: str | None = None, headers: Mapping[str, str] | None = None
) -> None:
    """Configure the OpenTelemetry tracer provider with an OTLP exporter."""

    global _TRACING_INITIALISED
    if _TRACING_INITIALISED:
        return

    resource = Resource.create({"service.name": service_name})
    tracer_provider = TracerProvider(resource=resource)

    effective_endpoint = (
        endpoint
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    )
    if not effective_endpoint:
        logger.warning(
            "distributed tracing disabled; no OTLP endpoint configured",
            extra={"service_name": service_name},
        )
        return

    try:
        exporter_headers = dict(headers) if headers is not None else None
        span_exporter = OTLPSpanExporter(endpoint=effective_endpoint, headers=exporter_headers)
    except Exception:  # pragma: no cover - exporter misconfiguration
        logger.exception("failed to initialise OTLP span exporter; tracing disabled")
        return

    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)
    _instrument_httpx()
    _TRACING_INITIALISED = True
    logger.info(
        "tracing initialised",
        extra={"service_name": service_name, "endpoint": effective_endpoint},
    )


def is_tracing_enabled() -> bool:
    """Return True when tracing has been initialised for the current process."""

    return _TRACING_INITIALISED


def instrument_fastapi_app(app: FastAPI) -> None:
    """Attach OpenTelemetry instrumentation to a FastAPI application."""

    tracer_provider = trace.get_tracer_provider()
    if isinstance(tracer_provider, TracerProvider):
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    else:  # pragma: no cover - defensive fallback
        FastAPIInstrumentor.instrument_app(app)


def _instrument_httpx() -> None:
    global _HTTPX_INSTRUMENTED
    if _HTTPX_INSTRUMENTED:
        return
    HTTPXClientInstrumentor().instrument()
    _HTTPX_INSTRUMENTED = True


def parse_exporter_headers(header_value: str | None) -> dict[str, str] | None:
    """Parse a comma-separated header string into a dict for OTLP exporters."""

    if not header_value:
        return None

    headers: dict[str, str] = {}
    parts = [segment.strip() for segment in header_value.split(",") if segment.strip()]
    for part in parts:
        if "=" not in part:
            logger.warning("ignoring malformed OTLP header segment", extra={"segment": part})
            continue
        key, value = part.split("=", 1)
        headers[key.strip()] = value.strip()
    return headers or None
