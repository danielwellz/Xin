"""Async pipeline orchestrating document ingestion into the vector store."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import Protocol

from chatbot.rag.chunking import Chunk, ChunkingConfig, chunk_markdown

from .errors import (
    EmbeddingError,
    FetchError,
    IngestionError,
    NormalizationError,
    PersistenceError,
)
from .models import (
    ChunkEmbedding,
    FetchedDocument,
    IngestionStatus,
    KnowledgeIngestJob,
    NormalizedDocument,
)

logger = logging.getLogger(__name__)


class DocumentFetcher(Protocol):
    async def fetch(self, job: KnowledgeIngestJob) -> list[FetchedDocument]:
        ...


class DocumentNormalizer(Protocol):
    def normalize(
        self, job: KnowledgeIngestJob, document: FetchedDocument
    ) -> NormalizedDocument:
        ...


class AsyncEmbedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class AsyncVectorStore(Protocol):
    async def upsert(
        self,
        collection: str,
        vectors: Iterable[ChunkEmbedding],
    ) -> None:
        ...


class StatusRepository(Protocol):
    async def mark_running(self, job_id: str) -> None:
        ...

    async def mark_completed(self, job_id: str, *, chunks: int, vectors: int) -> None:
        ...

    async def mark_failed(self, job_id: str, *, reason: str) -> None:
        ...


class ProgressPublisher(Protocol):
    async def publish(
        self,
        *,
        job: KnowledgeIngestJob,
        status: IngestionStatus,
        stage: str,
        detail: dict[str, object] | None = None,
    ) -> None:
        ...


class IngestionPipeline:
    """Coordinates the ingestion workflow for a single job."""

    def __init__(
        self,
        *,
        fetcher: DocumentFetcher,
        normalizer: DocumentNormalizer,
        embedder: AsyncEmbedder,
        vector_store: AsyncVectorStore,
        status_repository: StatusRepository,
        progress_publisher: ProgressPublisher,
        chunking_config: ChunkingConfig | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._normalizer = normalizer
        self._embedder = embedder
        self._vector_store = vector_store
        self._status_repository = status_repository
        self._progress = progress_publisher
        self._chunking_config = chunking_config or ChunkingConfig()

    async def run(self, job: KnowledgeIngestJob) -> None:
        """Execute the ingestion pipeline for the provided job."""

        await self._status_repository.mark_running(job.job_id)
        await self._progress.publish(
            job=job, status=IngestionStatus.RUNNING, stage="started"
        )

        try:
            fetched = await self._fetch_documents(job)
            normalized = self._normalize_documents(job, fetched)
            chunks = self._chunk_documents(job, normalized)
            embeddings = await self._embed_chunks(job, chunks)
            await self._persist_vectors(job, embeddings)
        except IngestionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging branch
            logger.exception(
                "unexpected error in ingestion pipeline", extra={"job_id": job.job_id}
            )
            raise PersistenceError(
                "unexpected ingestion failure", retryable=False
            ) from exc

        await self._status_repository.mark_completed(
            job.job_id,
            chunks=len(embeddings),
            vectors=len(embeddings),
        )
        await self._progress.publish(
            job=job,
            status=IngestionStatus.COMPLETED,
            stage="completed",
            detail={"chunks": len(embeddings)},
        )

    async def _fetch_documents(self, job: KnowledgeIngestJob) -> list[FetchedDocument]:
        try:
            documents = await self._fetcher.fetch(job)
        except IngestionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging branch
            logger.exception("failed to fetch documents", extra={"job_id": job.job_id})
            raise FetchError(
                "failed to fetch source documents", retryable=True
            ) from exc

        if not documents:
            raise FetchError("no documents returned from storage", retryable=False)

        await self._progress.publish(
            job=job,
            status=IngestionStatus.RUNNING,
            stage="fetched",
            detail={"documents": len(documents)},
        )
        return documents

    def _normalize_documents(
        self,
        job: KnowledgeIngestJob,
        documents: list[FetchedDocument],
    ) -> list[NormalizedDocument]:
        normalized: list[NormalizedDocument] = []
        try:
            for document in documents:
                normalized.append(self._normalizer.normalize(job, document))
        except IngestionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging branch
            logger.exception(
                "failed to normalize documents", extra={"job_id": job.job_id}
            )
            raise NormalizationError(
                "failed to normalize document", retryable=False
            ) from exc

        if not normalized:
            raise NormalizationError(
                "all documents were filtered during normalization", retryable=False
            )

        return normalized

    def _chunk_documents(
        self,
        job: KnowledgeIngestJob,
        documents: list[NormalizedDocument],
    ) -> list[Chunk]:
        chunking_config = self._chunking_config
        all_chunks: list[Chunk] = []
        for doc in documents:
            metadata = {
                "tenant_id": job.tenant_id,
                "brand_id": job.brand_id,
                "document_id": doc.document_id,
                **{k: str(v) for k, v in doc.metadata.items()},
            }
            doc_chunks = chunk_markdown(doc.text, chunking_config, metadata=metadata)
            all_chunks.extend(doc_chunks)

        if not all_chunks:
            raise NormalizationError(
                "no chunks produced from documents", retryable=False
            )

        return all_chunks

    async def _embed_chunks(
        self,
        job: KnowledgeIngestJob,
        chunks: list[Chunk],
    ) -> list[ChunkEmbedding]:
        texts = [chunk.content for chunk in chunks]

        try:
            vectors = await self._embedder.embed(texts)
        except IngestionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging branch
            logger.exception("failed to embed chunks", extra={"job_id": job.job_id})
            raise EmbeddingError("embedding service failed", retryable=True) from exc

        if len(vectors) != len(chunks):
            raise EmbeddingError("embedding count mismatch", retryable=True)

        embeddings: list[ChunkEmbedding] = []
        for chunk, embedding in zip(chunks, vectors, strict=False):
            if chunk.metadata.get("format") == "heading":
                continue
            embeddings.append(
                ChunkEmbedding(
                    chunk_id=chunk.id,
                    text=chunk.content,
                    embedding=list(map(float, embedding)),
                    metadata=chunk.metadata,
                )
            )

        await self._progress.publish(
            job=job,
            status=IngestionStatus.RUNNING,
            stage="embedded",
            detail={"chunks": len(embeddings)},
        )
        return embeddings

    async def _persist_vectors(
        self, job: KnowledgeIngestJob, embeddings: list[ChunkEmbedding]
    ) -> None:
        try:
            await self._vector_store.upsert(job.namespace, embeddings)
        except IngestionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging branch
            logger.exception("failed to persist vectors", extra={"job_id": job.job_id})
            raise PersistenceError(
                "vector store persistence failed", retryable=True
            ) from exc

        await self._progress.publish(
            job=job,
            status=IngestionStatus.RUNNING,
            stage="persisted",
            detail={"vectors": len(embeddings)},
        )
