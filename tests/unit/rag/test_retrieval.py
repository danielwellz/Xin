from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import pytest

from chatbot.rag.chunking import Chunk
from chatbot.rag.retrieval import (
    initialize_brand_knowledge,
    refresh_brand_knowledge,
    retrieve_context,
)
from chatbot.rag.vector_store import InMemoryVectorStore

pytestmark = pytest.mark.unit


class StubEmbeddingService:
    """Deterministic embedding stub based on simple token counts."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            tokens = text.lower().split()
            embeddings.append(
                [
                    float(len(tokens)),
                    float(sum(len(token) for token in tokens)),
                ]
            )
        return embeddings

    async def embed_async(self, texts: Sequence[str]) -> list[list[float]]:
        return self.embed(texts)


def _chunk(content: str) -> Chunk:
    return Chunk(id=str(uuid4()), content=content, metadata={"source": "stub"})


def test_initialize_and_retrieve_prioritizes_relevant_chunks() -> None:
    store = InMemoryVectorStore()
    embeddings = StubEmbeddingService()

    tenant_id = uuid4()
    brand_id = uuid4()

    chunks = [
        _chunk("Our return policy allows 30 day returns on all items."),
        _chunk("Shipping typically takes 3 to 5 business days within the US."),
        _chunk("Customer support can be reached via email or phone."),
    ]

    initialize_brand_knowledge(
        tenant_id=tenant_id,
        brand_id=brand_id,
        chunks=chunks,
        embedding_service=embeddings,
        vector_store=store,
    )

    results = retrieve_context(
        tenant_id=tenant_id,
        brand_id=brand_id,
        message="How long does shipping take?",
        embedding_service=embeddings,
        vector_store=store,
        top_k=2,
    )

    assert results
    assert "shipping" in results[0].text.lower()
    assert results[0].metadata["tenant_id"] == str(tenant_id)
    assert results[0].metadata["brand_id"] == str(brand_id)


def test_refresh_brand_knowledge_merges_content() -> None:
    store = InMemoryVectorStore()
    embeddings = StubEmbeddingService()

    tenant_id = uuid4()
    brand_id = uuid4()

    first_chunk = _chunk("Legacy information about warranties.")
    initialize_brand_knowledge(
        tenant_id=tenant_id,
        brand_id=brand_id,
        chunks=[first_chunk],
        embedding_service=embeddings,
        vector_store=store,
    )

    new_chunk = _chunk("Updated warranty includes 2 year coverage.")
    refresh_brand_knowledge(
        tenant_id=tenant_id,
        brand_id=brand_id,
        chunks=[new_chunk],
        embedding_service=embeddings,
        vector_store=store,
    )

    results = retrieve_context(
        tenant_id=tenant_id,
        brand_id=brand_id,
        message="Tell me about warranty coverage.",
        embedding_service=embeddings,
        vector_store=store,
    )

    assert len(results) >= 1
    texts = " ".join(result.text for result in results).lower()
    assert "updated warranty" in texts or "legacy information" in texts
