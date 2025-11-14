"""Postgres repository for ingestion job status tracking."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from psycopg2 import pool

from chatbot.core.db.models import IngestionJobStatus, KnowledgeSourceStatus


@dataclass(slots=True)
class PostgresStatusSettings:
    """Connection and table settings for status updates."""

    dsn: str
    min_connections: int = 1
    max_connections: int = 5
    table_name: str = "knowledge_sources"


class PostgresStatusRepository:
    """Update ingestion job statuses using a psycopg2 connection pool."""

    def __init__(self, *, settings: PostgresStatusSettings) -> None:
        self._settings = settings
        self._pool = pool.SimpleConnectionPool(
            settings.min_connections,
            settings.max_connections,
            dsn=settings.dsn,
        )

    async def mark_running(self, job_id: str) -> None:
        await self._execute(
            f"""
            UPDATE {self._settings.table_name}
               SET status = %s,
                   failure_reason = NULL,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (KnowledgeSourceStatus.PROCESSING.value, job_id),
        )
        await self._update_ingestion_job(job_id, IngestionJobStatus.RUNNING.value)

    async def mark_completed(self, job_id: str, *, chunks: int, vectors: int) -> None:
        await self._execute(
            f"""
            UPDATE {self._settings.table_name}
               SET status = %s,
                   failure_reason = NULL,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (KnowledgeSourceStatus.READY.value, job_id),
        )
        await self._update_ingestion_job(job_id, IngestionJobStatus.COMPLETED.value)

    async def mark_failed(self, job_id: str, *, reason: str) -> None:
        await self._execute(
            f"""
            UPDATE {self._settings.table_name}
               SET status = %s,
                   failure_reason = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (KnowledgeSourceStatus.FAILED.value, reason, job_id),
        )
        await self._update_ingestion_job(
            job_id, IngestionJobStatus.FAILED.value, reason=reason
        )

    async def _execute(self, query: str, params: tuple[object, ...]) -> None:
        await asyncio.to_thread(self._execute_sync, query, params)

    def _execute_sync(self, query: str, params: tuple[object, ...]) -> None:
        connection = self._pool.getconn()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
            connection.commit()
        finally:
            self._pool.putconn(connection)

    async def close(self) -> None:
        await asyncio.to_thread(self._pool.closeall)

    async def _update_ingestion_job(
        self, job_id: str, status: str, reason: str | None = None
    ) -> None:
        await self._execute(
            """
            UPDATE ingestion_jobs
               SET status = %s,
                   started_at = COALESCE(started_at, NOW()),
                   completed_at = CASE WHEN %s IN ('completed', 'failed') THEN NOW() ELSE completed_at END,
                   failure_reason = %s
             WHERE id = %s
            """,
            (status, status, reason, job_id),
        )
