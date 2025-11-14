"""Async Qdrant adapter used for ingestion persistence."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Iterable

import httpx

from chatbot.apps.ingestion.errors import PersistenceError
from chatbot.apps.ingestion.models import ChunkEmbedding

logger = logging.getLogger(__name__)


class QdrantVectorStoreAdapter:
    """Persist embeddings into Qdrant collections segmented by tenant/brand."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str | None = None,
        vector_size: int = 1536,
        distance: str = "Cosine",
        timeout: float = 10.0,
        base_collection: str = "knowledge",
    ) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._vector_size = vector_size
        self._distance = distance
        self._client = httpx.AsyncClient(timeout=timeout)
        self._base_collection = base_collection
        self._ensured_collections: set[str] = set()
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self._client.aclose()

    async def upsert(self, collection: str, vectors: Iterable[ChunkEmbedding]) -> None:
        collection_name = self._collection_name(collection)
        await self._ensure_collection(collection_name)

        points = [
            {
                "id": embedding.chunk_id or str(uuid.uuid4()),
                "vector": list(embedding.embedding),
                "payload": {
                    "text": embedding.text,
                    "metadata": embedding.metadata,
                    "collection": collection_name,
                },
            }
            for embedding in vectors
        ]

        if not points:
            raise PersistenceError(
                "no embeddings supplied for persistence", retryable=False
            )

        try:
            response = await self._client.put(
                f"{self._url}/collections/{collection_name}/points?wait=true",
                json={"points": points},
                headers=self._headers(),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "qdrant responded with error",
                extra={"status": exc.response.status_code, "body": exc.response.text},
            )
            raise PersistenceError(
                "qdrant rejected persistence request", retryable=True
            ) from exc
        except httpx.HTTPError as exc:
            raise PersistenceError("failed to reach qdrant", retryable=True) from exc

    def _collection_name(self, namespace: str) -> str:
        safe_namespace = namespace.replace(":", "__")
        return f"{self._base_collection}_{safe_namespace}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["api-key"] = self._api_key
        return headers

    async def _ensure_collection(self, collection_name: str) -> None:
        async with self._lock:
            if collection_name in self._ensured_collections:
                return
            payload = {
                "vectors": {
                    "size": self._vector_size,
                    "distance": self._distance,
                }
            }
            try:
                response = await self._client.put(
                    f"{self._url}/collections/{collection_name}",
                    json=payload,
                    headers=self._headers(),
                )
            except httpx.HTTPError as exc:
                logger.error("qdrant ensure collection failed", exc_info=exc)
                raise PersistenceError(
                    "unable to ensure qdrant collection", retryable=True
                ) from exc

            if response.status_code not in (200, 201):
                logger.warning(
                    "qdrant collection ensure returned non-success",
                    extra={"status": response.status_code, "body": response.text},
                )
            self._ensured_collections.add(collection_name)
