"""Vector store integrations for retrieval workflows."""

from __future__ import annotations

import logging
import math
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class VectorDocument:
    """Represents a stored vector and associated metadata."""

    id: str
    text: str
    embedding: Sequence[float]
    metadata: dict[str, str] = field(default_factory=dict)


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore:
    """Common interface for vector storage backends."""

    def upsert(self, namespace: str, documents: Iterable[VectorDocument]) -> None:
        raise NotImplementedError

    def delete_namespace(self, namespace: str) -> None:
        raise NotImplementedError

    def search(
        self, namespace: str, query: Sequence[float], top_k: int = 5
    ) -> list[VectorDocument]:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """Simple vector store implementation backed by in-memory dictionaries."""

    def __init__(self) -> None:
        self._store: dict[str, list[VectorDocument]] = {}

    def upsert(self, namespace: str, documents: Iterable[VectorDocument]) -> None:
        entries = self._store.setdefault(namespace, [])
        existing = {doc.id: doc for doc in entries}
        for doc in documents:
            existing[doc.id] = doc
        self._store[namespace] = list(existing.values())

    def delete_namespace(self, namespace: str) -> None:
        self._store.pop(namespace, None)

    def search(
        self, namespace: str, query: Sequence[float], top_k: int = 5
    ) -> list[VectorDocument]:
        documents = self._store.get(namespace, [])
        scored = [(doc, _cosine_similarity(query, doc.embedding)) for doc in documents]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [doc for doc, score in scored[:top_k] if score > 0]


class QdrantVectorStore(VectorStore):
    """HTTP integration with Qdrant vector database."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str | None = None,
        timeout: float = 10.0,
        collection_name: str = "knowledge_chunks",
    ) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._collection = collection_name
        self._client = httpx.Client(timeout=timeout)
        self._init_collection()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["api-key"] = self._api_key
        return headers

    def _init_collection(self) -> None:
        payload = {
            "vectors": {
                "size": 1536,
                "distance": "Cosine",
            }
        }
        response = self._client.put(
            f"{self._url}/collections/{self._collection}",
            json=payload,
            headers=self._headers(),
        )
        if response.status_code not in (200, 201):
            logger.warning(
                "failed to ensure qdrant collection exists",
                extra={"status": response.status_code, "body": response.text},
            )

    def upsert(self, namespace: str, documents: Iterable[VectorDocument]) -> None:
        points = [
            {
                "id": doc.id or str(uuid.uuid4()),
                "vector": list(doc.embedding),
                "payload": {"text": doc.text, "metadata": doc.metadata, "namespace": namespace},
            }
            for doc in documents
        ]

        response = self._client.put(
            f"{self._url}/collections/{self._collection}/points?wait=true",
            json={"points": points},
            headers=self._headers(),
        )
        response.raise_for_status()

    def delete_namespace(self, namespace: str) -> None:
        response = self._client.post(
            f"{self._url}/collections/{self._collection}/points/delete?wait=true",
            json={"filter": {"must": [{"key": "namespace", "match": {"value": namespace}}]}},
            headers=self._headers(),
        )
        response.raise_for_status()

    def search(
        self, namespace: str, query: Sequence[float], top_k: int = 5
    ) -> list[VectorDocument]:
        response = self._client.post(
            f"{self._url}/collections/{self._collection}/points/search",
            json={
                "vector": list(query),
                "limit": top_k,
                "with_payload": True,
                "filter": {"must": [{"key": "namespace", "match": {"value": namespace}}]},
            },
            headers=self._headers(),
        )
        response.raise_for_status()
        payload = response.json()
        results: list[VectorDocument] = []
        for item in payload.get("result", []):
            payload_data = item.get("payload", {})
            metadata = payload_data.get("metadata") or {}
            text = payload_data.get("text") or ""
            doc_id = str(item.get("id"))
            results.append(
                VectorDocument(
                    id=doc_id,
                    text=text,
                    embedding=item.get("vector") or [],
                    metadata={"score": str(item.get("score", 0.0)), **metadata},
                )
            )
        return results
