"""Reusable FastAPI middleware for correlation IDs, logging, and metrics."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

import structlog
from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging import get_logger

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)

REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds",
    "Latency of HTTP requests.",
    ["service", "method", "route", "status_code"],
)

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total number of processed HTTP requests.",
    ["service", "method", "route", "status_code"],
)


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current context."""

    return _correlation_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that injects correlation IDs, logs requests, and records metrics."""

    def __init__(self, app: ASGIApp, *, service_name: str) -> None:
        super().__init__(app)
        self._service_name = service_name
        self._logger = get_logger(service_name)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = (
            request.headers.get("x-request-id") or _generate_correlation_id()
        )
        token = _correlation_id_ctx.set(correlation_id)
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        start = time.perf_counter()
        response: Response | None = None
        status_code = 500
        error_logged = False

        try:
            response = await call_next(request)
            status_code = getattr(response, "status_code", 200)
            return response
        except Exception:
            error_logged = True
            self._logger.exception(
                "http.request.error",
                method=request.method,
                path=request.url.path,
                route=_route_from_scope(request),
                status_code=status_code,
                correlation_id=correlation_id,
            )
            raise
        finally:
            duration = time.perf_counter() - start
            route = _route_from_scope(request)
            status_value = str(status_code)

            REQUEST_COUNTER.labels(
                self._service_name, request.method, route, status_value
            ).inc()
            REQUEST_LATENCY.labels(
                self._service_name, request.method, route, status_value
            ).observe(duration)

            if response is not None:
                response.headers["X-Request-ID"] = correlation_id

            if not error_logged:
                self._logger.info(
                    "http.request.completed",
                    method=request.method,
                    path=request.url.path,
                    route=route,
                    status_code=status_code,
                    duration_ms=round(duration * 1000, 2),
                    correlation_id=correlation_id,
                )

            structlog.contextvars.unbind_contextvars("correlation_id")
            _correlation_id_ctx.reset(token)


def metrics_response() -> Response:
    """Generate a Prometheus metrics response."""

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _generate_correlation_id() -> str:
    return uuid.uuid4().hex


def _route_from_scope(request: Request) -> str:
    route = request.scope.get("route")
    if route and getattr(route, "path", None):
        return route.path
    return request.url.path
