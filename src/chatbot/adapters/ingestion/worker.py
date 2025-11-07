"""ARQ worker integration for knowledge ingestion jobs."""

from __future__ import annotations

import logging
from typing import Any

from arq import Retry
from arq.connections import RedisSettings
from prometheus_client import start_http_server
from redis.asyncio import Redis

from chatbot.adapters.ingestion.postgres import PostgresStatusRepository, PostgresStatusSettings
from chatbot.adapters.ingestion.redis import (
    ProgressPublisherSettings,
    RedisPoisonQueue,
    RedisProgressPublisher,
)
from chatbot.adapters.ingestion.s3 import MinioDocumentFetcher, MinioFetcherSettings
from chatbot.adapters.ingestion.vector_store import QdrantVectorStoreAdapter
from chatbot.adapters.ingestion.embedding import AsyncEmbeddingAdapter
from chatbot.adapters.ingestion.errors import IngestionError
from chatbot.adapters.ingestion.models import IngestionStatus, KnowledgeIngestJob
from chatbot.adapters.ingestion.normalizer import MarkdownNormalizer
from chatbot.adapters.ingestion.pipeline import IngestionPipeline
from chatbot.adapters.ingestion.settings import IngestionWorkerSettings
from chatbot.utils.retry import exponential_backoff
from chatbot.core.logging import configure_logging
from chatbot.core.telemetry import init_tracing, is_tracing_enabled, parse_exporter_headers
from chatbot.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


_METRICS_STARTED = False


async def startup(ctx: dict[str, Any]) -> None:
    """Initialise connections and shared dependencies."""

    settings = IngestionWorkerSettings()
    ctx["settings"] = settings

    configure_logging()
    init_tracing(
        service_name="ingestion_worker",
        endpoint=settings.otlp_endpoint,
        headers=parse_exporter_headers(settings.otlp_headers),
    )
    if is_tracing_enabled():
        logger.info("tracing active", extra={"service_name": "ingestion_worker"})
    else:
        logger.warning(
            "tracing disabled; operating without OTLP exporter",
            extra={"service_name": "ingestion_worker"},
        )
    _ensure_metrics_exporter(settings)

    redis_client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
    )

    fetcher = MinioDocumentFetcher(
        settings=MinioFetcherSettings(
            endpoint_url=settings.minio_endpoint_url,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            region_name=settings.minio_region,
        )
    )

    embedding_service = EmbeddingService(settings=settings.embedding_settings())
    embedder = AsyncEmbeddingAdapter(embedding_service)

    vector_store = QdrantVectorStoreAdapter(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        vector_size=settings.qdrant_vector_size,
        base_collection=settings.qdrant_collection_prefix,
    )

    status_repository = PostgresStatusRepository(
        settings=PostgresStatusSettings(dsn=settings.postgres_dsn)
    )

    progress_publisher = RedisProgressPublisher(
        redis=redis_client,
        settings=ProgressPublisherSettings(
            channel_template=settings.redis_progress_channel_template
        ),
    )

    pipeline = IngestionPipeline(
        fetcher=fetcher,
        normalizer=MarkdownNormalizer(),
        embedder=embedder,
        vector_store=vector_store,
        status_repository=status_repository,
        progress_publisher=progress_publisher,
    )

    ctx["pipeline"] = pipeline
    ctx["redis"] = redis_client
    ctx["poison_queue"] = RedisPoisonQueue(
        redis=redis_client,
        key=settings.redis_poison_key,
    )
    ctx["status_repository"] = status_repository
    ctx["vector_store"] = vector_store
    ctx["progress_publisher"] = progress_publisher


async def shutdown(ctx: dict[str, Any]) -> None:
    """Clean up allocated resources."""

    vector_store = ctx.get("vector_store")
    if vector_store:
        await vector_store.close()

    status_repository = ctx.get("status_repository")
    if status_repository:
        await status_repository.close()

    redis_client: Redis | None = ctx.get("redis")
    if redis_client:
        await redis_client.close()
        await redis_client.wait_closed()


async def process_knowledge_ingest(ctx: dict[str, Any], payload: dict[str, Any]) -> dict[str, str]:
    """Process a knowledge ingestion job and return completion metadata."""

    job = KnowledgeIngestJob.model_validate(payload)
    pipeline: IngestionPipeline = ctx["pipeline"]
    settings: IngestionWorkerSettings = ctx["settings"]
    attempt = ctx.get("job_try", 1)

    try:
        await pipeline.run(job)
        return {"status": IngestionStatus.COMPLETED.value}
    except IngestionError as exc:
        progress: RedisProgressPublisher = ctx["progress_publisher"]

        if attempt >= settings.arq_max_retries or not exc.retryable:
            status_repo: PostgresStatusRepository = ctx["status_repository"]
            await status_repo.mark_failed(job.job_id, reason=exc.message)

            await progress.publish(
                job=job,
                status=IngestionStatus.FAILED,
                stage="failed",
                detail={"message": exc.message, "attempt": attempt},
            )

            poison_queue: RedisPoisonQueue = ctx["poison_queue"]
            await poison_queue.push(job, exc, attempt=attempt)
            raise

        delay = exponential_backoff(
            attempt,
            base=settings.backoff_base,
            factor=settings.backoff_factor,
            max_delay=settings.backoff_max,
        )

        await progress.publish(
            job=job,
            status=IngestionStatus.RUNNING,
            stage="retrying",
            detail={"message": exc.message, "attempt": attempt, "retry_in": round(delay, 2)},
        )

        raise Retry(defer=delay) from exc
    except Exception:
        logger.exception("unhandled exception during ingestion job", extra={"job_id": job.job_id})
        progress: RedisProgressPublisher = ctx["progress_publisher"]
        status_repo: PostgresStatusRepository = ctx["status_repository"]
        poison_queue: RedisPoisonQueue = ctx["poison_queue"]
        message = "unexpected failure processing ingestion job"
        await status_repo.mark_failed(job.job_id, reason=message)
        await progress.publish(
            job=job,
            status=IngestionStatus.FAILED,
            stage="failed",
            detail={"message": message, "attempt": attempt},
        )
        await poison_queue.push(
            job,
            IngestionError(message, retryable=False),
            attempt=attempt,
        )
        raise


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [process_knowledge_ingest]
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = 60 * 10

    @staticmethod
    def redis_settings() -> RedisSettings:
        settings = IngestionWorkerSettings()
        return RedisSettings(
            host=settings.redis_host,
            port=settings.redis_port,
            database=settings.redis_db,
            password=settings.redis_password,
        )

    @staticmethod
    def queue_name() -> str:
        settings = IngestionWorkerSettings()
        return settings.redis_queue_name


def _ensure_metrics_exporter(settings: IngestionWorkerSettings) -> None:
    global _METRICS_STARTED
    if _METRICS_STARTED or settings.metrics_port is None:
        return

    start_http_server(settings.metrics_port, addr=settings.metrics_host)
    logger.info(
        "prometheus exporter running",
        extra={"host": settings.metrics_host, "port": settings.metrics_port},
    )
    _METRICS_STARTED = True
