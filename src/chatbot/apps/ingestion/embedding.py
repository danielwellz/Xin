"""Adapter bridging the shared embedding service to the ingestion pipeline."""

from __future__ import annotations

from chatbot.rag.embeddings import EmbeddingService

from .errors import EmbeddingError


class AsyncEmbeddingAdapter:
    """Expose the embedding service with the pipeline's async interface."""

    def __init__(self, service: EmbeddingService) -> None:
        self._service = service

    async def embed(self, texts):
        try:
            return await self._service.embed_async(texts)
        except RuntimeError as exc:  # pragma: no cover - protective guardrail
            raise EmbeddingError(str(exc), retryable=False) from exc
