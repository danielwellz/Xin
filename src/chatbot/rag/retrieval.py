"""High-level retrieval workflows for brand knowledge."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from .chunking import Chunk
from .embeddings import EmbeddingService
from .vector_store import VectorDocument, VectorStore

logger = logging.getLogger(__name__)


def _namespace(tenant_id: UUID | str, brand_id: UUID | str) -> str:
    return f"{tenant_id}:{brand_id}"


def initialize_brand_knowledge(
    *,
    tenant_id: UUID | str,
    brand_id: UUID | str,
    chunks: Sequence[Chunk],
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
) -> None:
    """Ingest a fresh set of chunks for a brand."""

    namespace = _namespace(tenant_id, brand_id)
    logger.info(
        "initializing brand knowledge", extra={"namespace": namespace, "count": len(chunks)}
    )
    vector_store.delete_namespace(namespace)
    _store_chunks(
        namespace,
        tenant_id=tenant_id,
        brand_id=brand_id,
        chunks=chunks,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )


def refresh_brand_knowledge(
    *,
    tenant_id: UUID | str,
    brand_id: UUID | str,
    chunks: Sequence[Chunk],
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
) -> None:
    """Refresh brand knowledge while preserving prior chunks."""

    namespace = _namespace(tenant_id, brand_id)
    logger.info("refreshing brand knowledge", extra={"namespace": namespace, "count": len(chunks)})
    _store_chunks(
        namespace,
        tenant_id=tenant_id,
        brand_id=brand_id,
        chunks=chunks,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )


def retrieve_context(
    *,
    tenant_id: UUID | str,
    brand_id: UUID | str,
    message: str,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    top_k: int = 5,
) -> list[VectorDocument]:
    """Retrieve relevant chunks for the provided message."""

    namespace = _namespace(tenant_id, brand_id)
    if not message.strip():
        return []

    embeddings = embedding_service.embed([message])
    if not embeddings:
        return []

    query_vector = embeddings[0]
    results = vector_store.search(namespace, query_vector, top_k=top_k)
    message_terms = {token.strip(".,!?") for token in message.lower().split() if token}
    if message_terms:
        scored = []
        for index, document in enumerate(results):
            text_terms = set(document.text.lower().split())
            overlap = sum(1 for term in message_terms if term and term in text_terms)
            scored.append((overlap, -index, document))
        scored.sort(reverse=True)
        results = [item[2] for item in scored]
    logger.debug(
        "retrieved context",
        extra={"namespace": namespace, "top_k": top_k, "result_count": len(results)},
    )
    return results


def _store_chunks(
    namespace: str,
    *,
    tenant_id: UUID | str,
    brand_id: UUID | str,
    chunks: Sequence[Chunk],
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
) -> None:
    if not chunks:
        logger.warning(
            "no chunks provided; skipping knowledge update", extra={"namespace": namespace}
        )
        return

    contents = [chunk.content for chunk in chunks]
    embeddings = embedding_service.embed(contents)
    if len(embeddings) != len(chunks):
        raise RuntimeError("embedding service did not return vectors for all chunks")
    base_metadata = {"tenant_id": str(tenant_id), "brand_id": str(brand_id)}
    documents = [
        VectorDocument(
            id=chunk.id,
            text=chunk.content,
            embedding=embedding,
            metadata={
                key: str(value)
                for key, value in {**base_metadata, **(chunk.metadata or {})}.items()
            },
        )
        for chunk, embedding in zip(chunks, embeddings, strict=False)
    ]
    vector_store.upsert(namespace, documents)
