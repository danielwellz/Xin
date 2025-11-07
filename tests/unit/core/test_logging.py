from __future__ import annotations

import json

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from chatbot.core.logging import configure_logging, get_logger

pytestmark = pytest.mark.unit


def test_structlog_injects_trace_context(capsys) -> None:
    configure_logging()

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    logger = get_logger("test")

    with tracer.start_as_current_span("logging-test"):
        logger.info("log_event", component="test")

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured

    record = json.loads(captured[-1])
    assert record["event"] == "log_event"
    assert record["component"] == "test"
    assert "trace_id" in record and len(record["trace_id"]) == 32
    assert "span_id" in record and len(record["span_id"]) == 16
