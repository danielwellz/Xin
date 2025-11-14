from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from chatbot.apps.ingestion.errors import EmbeddingError, FetchError
from chatbot.apps.ingestion.models import (
    FetchedDocument,
    IngestionStatus,
    KnowledgeIngestJob,
)
from chatbot.apps.ingestion.normalizer import MarkdownNormalizer
from chatbot.apps.ingestion.pipeline import IngestionPipeline

pytestmark = pytest.mark.unit


class StubFetcher:
    def __init__(
        self,
        documents: list[FetchedDocument] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._documents = documents or []
        self._exc = exc

    async def fetch(self, job: KnowledgeIngestJob) -> list[FetchedDocument]:
        if self._exc:
            raise self._exc
        return list(self._documents)


class StubEmbedder:
    def __init__(self, vectors: list[list[float]] | None = None) -> None:
        self._vectors = vectors
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        if self._vectors is None:
            return [[float(index)] for index, _ in enumerate(texts)]
        return list(self._vectors)


class StubVectorStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list]] = []

    async def upsert(self, collection: str, vectors):
        self.calls.append((collection, list(vectors)))


@dataclass
class RecorderStatusRepository:
    running: list[str] = field(default_factory=list)
    completed: list[tuple[str, int, int]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    async def mark_running(self, job_id: str) -> None:
        self.running.append(job_id)

    async def mark_completed(self, job_id: str, *, chunks: int, vectors: int) -> None:
        self.completed.append((job_id, chunks, vectors))

    async def mark_failed(self, job_id: str, *, reason: str) -> None:
        self.failed.append((job_id, reason))


@dataclass
class RecorderProgressPublisher:
    events: list[tuple[str, IngestionStatus, str, dict[str, object]]] = field(
        default_factory=list
    )

    async def publish(
        self,
        *,
        job,
        status: IngestionStatus,
        stage: str,
        detail: dict[str, object] | None = None,
    ):
        self.events.append((job.job_id, status, stage, detail or {}))


def make_job(**overrides):
    data = {
        "job_id": "job-123",
        "tenant_id": "tenant-a",
        "brand_id": "brand-b",
        "sourceUri": "s3://bucket/object.md",
    }
    data.update(overrides)
    return KnowledgeIngestJob(**data)


@pytest.mark.asyncio
async def test_pipeline_happy_path():
    job = make_job()
    fetcher = StubFetcher(
        documents=[
            FetchedDocument(
                document_id="doc1",
                raw_bytes=b"# Title\nBody text",
                metadata={},
            )
        ]
    )
    embedder = StubEmbedder()
    vector_store = StubVectorStore()
    status_repo = RecorderStatusRepository()
    progress = RecorderProgressPublisher()

    pipeline = IngestionPipeline(
        fetcher=fetcher,
        normalizer=MarkdownNormalizer(),
        embedder=embedder,
        vector_store=vector_store,
        status_repository=status_repo,
        progress_publisher=progress,
    )

    await pipeline.run(job)

    assert status_repo.running == [job.job_id]
    assert status_repo.completed == [(job.job_id, 1, 1)]
    assert not status_repo.failed

    assert vector_store.calls
    collection, vectors = vector_store.calls[0]
    assert collection == job.namespace
    assert vectors[0].metadata["tenant_id"] == job.tenant_id

    stages = [stage for _, _, stage, _ in progress.events]
    assert stages == ["started", "fetched", "embedded", "persisted", "completed"]


@pytest.mark.asyncio
async def test_pipeline_raises_on_fetch_failure():
    job = make_job()
    fetcher = StubFetcher(exc=FetchError("boom", retryable=True))
    pipeline = IngestionPipeline(
        fetcher=fetcher,
        normalizer=MarkdownNormalizer(),
        embedder=StubEmbedder(),
        vector_store=StubVectorStore(),
        status_repository=RecorderStatusRepository(),
        progress_publisher=RecorderProgressPublisher(),
    )

    with pytest.raises(FetchError):
        await pipeline.run(job)


@pytest.mark.asyncio
async def test_pipeline_detects_embedding_mismatch():
    job = make_job()
    fetcher = StubFetcher(
        documents=[
            FetchedDocument(
                document_id="doc1",
                raw_bytes=b"# H\nBody",
                metadata={},
            )
        ]
    )

    pipeline = IngestionPipeline(
        fetcher=fetcher,
        normalizer=MarkdownNormalizer(),
        # Return only one vector regardless of chunk count.
        embedder=StubEmbedder(vectors=[[0.1, 0.2]]),
        vector_store=StubVectorStore(),
        status_repository=RecorderStatusRepository(),
        progress_publisher=RecorderProgressPublisher(),
    )

    with pytest.raises(EmbeddingError):
        await pipeline.run(job)
