from __future__ import annotations

import pytest

from chatbot.core.telemetry import parse_exporter_headers

pytestmark = pytest.mark.unit


def test_parse_exporter_headers_handles_malformed_segments(caplog):
    headers = parse_exporter_headers("authorization=Bearer token,invalid,env=prod")
    assert headers == {"authorization": "Bearer token", "env": "prod"}
