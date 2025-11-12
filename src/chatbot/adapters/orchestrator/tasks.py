"""Async helpers for publishing ingestion jobs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from chatbot.core.config import IngestionQueueSettings

from .services import KnowledgeRegistrationResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QueueConfig:
    """Runtime configuration for the ingestion queue."""

    redis_settings: RedisSettings


def _build_queue_config(settings: IngestionQueueSettings) -> QueueConfig:
    redis_settings = RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
        password=settings.redis_password,
    )
    return QueueConfig(
        redis=redis_settings,
        queue_name=settings.queue_name,
    )


class IngestionJobPublisher:
    """Publish `KnowledgeIngestJob` payloads to the ARQ worker queue."""

    def __init__(self, queue_settings: IngestionQueueSettings) -> None:
        self._config = _build_queue_config(queue_settings)
        self._pool: ArqRedis | None = None
        self._lock = asyncio.Lock()

    async def enqueue_job(self, registration: KnowledgeRegistrationResult) -> str:
        """Schedule an ingestion job for the provided knowledge registration."""

        payload: dict[str, Any] = {
            "job_id": str(registration.knowledge.id),
            "tenant_id": str(registration.tenant_id),
            "brand_id": str(registration.brand_id),
            "sourceUri": registration.source_uri,
            "contentType": registration.content_type,
            "metadata": {
                "filename": registration.filename,
                "knowledge_source_id": str(registration.knowledge.id),
            },
        }

        pool = await self._ensure_pool()
        await pool.enqueue_job("process_knowledge_ingest", payload)
        return payload["job_id"]

    async def close(self) -> None:
        """Close the underlying Redis pool."""

        async with self._lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None

    async def _ensure_pool(self) -> ArqRedis:
        if self._pool is not None:
            return self._pool

        async with self._lock:
            if self._pool is None:
                logger.info("connecting to ingestion queue")
                self._pool = await create_pool(self._config.redis_settings)
        return self._pool
