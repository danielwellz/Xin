from __future__ import annotations

import logging
from typing import Any

import pytest

from chatbot.core import telemetry
from chatbot.core.telemetry import init_tracing, is_tracing_enabled, parse_exporter_headers

pytestmark = pytest.mark.unit


def test_parse_exporter_headers_handles_malformed_segments(caplog):
    headers = parse_exporter_headers("authorization=Bearer token,invalid,env=prod")
    assert headers == {"authorization": "Bearer token", "env": "prod"}


def test_init_tracing_logs_warning_when_endpoint_missing(monkeypatch, caplog):
    monkeypatch.setattr(telemetry, "_TRACING_INITIALISED", False)
    monkeypatch.setattr(telemetry, "_HTTPX_INSTRUMENTED", False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)

    caplog.set_level(logging.WARNING)

    init_tracing("test-service")

    assert any(
        "distributed tracing disabled" in record.message for record in caplog.records
    )
    assert not is_tracing_enabled()


def test_init_tracing_logs_success_when_endpoint_supplied(monkeypatch, caplog):
    class DummyExporter:  # pragma: no cover - simple stub
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    class DummyProcessor:  # pragma: no cover - simple stub
        def __init__(self, exporter: DummyExporter) -> None:
            self.exporter = exporter

    monkeypatch.setattr(telemetry, "OTLPSpanExporter", DummyExporter)
    monkeypatch.setattr(telemetry, "BatchSpanProcessor", DummyProcessor)
    monkeypatch.setattr(telemetry, "_instrument_httpx", lambda: None)
    monkeypatch.setattr(telemetry.trace, "set_tracer_provider", lambda provider: None)
    monkeypatch.setattr(telemetry, "_TRACING_INITIALISED", False)
    monkeypatch.setattr(telemetry, "_HTTPX_INSTRUMENTED", False)

    caplog.set_level(logging.INFO)

    init_tracing("test-service", endpoint="http://collector:4318/v1/traces")

    assert is_tracing_enabled()
    assert any("tracing initialised" in record.message for record in caplog.records)
