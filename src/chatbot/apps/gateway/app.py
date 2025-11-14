"""FastAPI application factory for the channel gateway service."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Response

from chatbot.core.logging import configure_logging
from chatbot.core.middleware import RequestContextMiddleware, metrics_response
from chatbot.core.telemetry import (
    init_tracing,
    instrument_fastapi_app,
    is_tracing_enabled,
    parse_exporter_headers,
)

from .dependencies import get_orchestrator_client, get_settings
from .routers import instagram, telegram, web, whatsapp

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the channel gateway FastAPI app."""

    settings = get_settings()
    configure_logging()
    init_tracing(
        service_name="channel_gateway",
        endpoint=settings.otlp_endpoint,
        headers=parse_exporter_headers(settings.otlp_headers),
    )
    if is_tracing_enabled():
        logger.info("tracing active", extra={"service_name": "channel_gateway"})
    else:
        logger.warning(
            "tracing disabled; operating without OTLP exporter",
            extra={"service_name": "channel_gateway"},
        )

    app = FastAPI(title="Xin Channel Gateway", version=settings.app_version)
    instrument_fastapi_app(app)
    app.add_middleware(RequestContextMiddleware, service_name="channel_gateway")

    app.include_router(instagram.router)
    app.include_router(whatsapp.router)
    app.include_router(telegram.router)
    app.include_router(web.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return metrics_response()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        client = get_orchestrator_client()
        await client.close()

    return app
