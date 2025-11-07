from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatbot.core.middleware import RequestContextMiddleware, get_correlation_id

pytestmark = pytest.mark.unit


def test_request_context_middleware_injects_correlation_id():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware, service_name="test-service")

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok", "correlation": get_correlation_id() or ""}

    client = TestClient(app)
    response = client.get("/ping")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.json()["correlation"] == response.headers["X-Request-ID"]
