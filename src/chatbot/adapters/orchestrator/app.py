"""FastAPI application factory for the orchestrator service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Response

from chatbot.core.config import AppSettings
from chatbot.core.http import HealthResponse
from chatbot.core.logging import configure_logging
from chatbot.core.middleware import RequestContextMiddleware, metrics_response
from chatbot.core.telemetry import init_tracing, instrument_fastapi_app, parse_exporter_headers

from .dependencies import get_settings
from .routers import conversations, knowledge, messages

SettingsDep = Annotated[AppSettings, Depends(get_settings)]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    configure_logging()
    init_tracing(
        service_name="orchestrator",
        endpoint=settings.telemetry.exporter_endpoint,
        headers=parse_exporter_headers(settings.telemetry.exporter_headers),
    )

    app = FastAPI(
        title="Xin Orchestrator Service",
        version=settings.app_version if hasattr(settings, "app_version") else "0.1.0",
    )

    instrument_fastapi_app(app)
    app.add_middleware(RequestContextMiddleware, service_name="orchestrator")

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health(_: SettingsDep) -> HealthResponse:
        return HealthResponse()

    app.include_router(messages.router)
    app.include_router(knowledge.router)
    app.include_router(conversations.router)

    @app.get("/metrics")
    async def metrics() -> Response:
        return metrics_response()

    return app
