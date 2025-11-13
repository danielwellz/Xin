"""Redis utilities for progress events and poison queue handling."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from chatbot.adapters.ingestion.errors import IngestionError
from chatbot.adapters.ingestion.models import IngestionStatus, KnowledgeIngestJob

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProgressPublisherSettings:
    """Settings controlling Redis channels."""

    channel_template: str = "ingestion:{tenant}:{brand}"


class RedisProgressPublisher:
    """Emit ingestion lifecycle events over Redis Pub/Sub."""

    def __init__(
        self,
        *,
        redis: Redis,
        settings: ProgressPublisherSettings | None = None,
    ) -> None:
        self._redis = redis
        self._settings = settings or ProgressPublisherSettings()

    async def publish(
        self,
        *,
        job: KnowledgeIngestJob,
        status: IngestionStatus,
        stage: str,
        detail: dict[str, object] | None = None,
    ) -> None:
        channel = self._settings.channel_template.format(
            tenant=job.tenant_id,
            brand=job.brand_id,
        )
        payload = {
            "job_id": job.job_id,
            "status": status.value,
            "stage": stage,
            "detail": _stringify(detail or {}),
        }
        try:
            await self._redis.publish(channel, json.dumps(payload))
        except Exception:  # pragma: no cover - best effort logging
            logger.exception(
                "failed to publish ingestion progress", extra={"channel": channel}
            )


class RedisPoisonQueue:
    """Persist failed jobs to a poison queue for manual inspection."""

    def __init__(self, *, redis: Redis, key: str = "ingestion:poison") -> None:
        self._redis = redis
        self._key = key

    async def push(
        self, job: KnowledgeIngestJob, error: IngestionError, *, attempt: int
    ) -> None:
        payload = {
            "job": job.dict(by_alias=True),
            "error": error.as_dict(),
            "attempt": attempt,
        }
        try:
            await self._redis.lpush(self._key, json.dumps(payload))
        except Exception:  # pragma: no cover - best effort logging
            logger.exception(
                "failed to record job in poison queue", extra={"queue": self._key}
            )


def _stringify(detail: dict[str, object]) -> dict[str, str]:
    return {key: str(value) for key, value in detail.items()}
