"""Embedding service with OpenAI and sentence-transformers backends."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from chatbot.core.config import LLMProvider

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class EmbeddingSettings:
    """Runtime settings for embedding generation."""

    provider: LLMProvider = LLMProvider.OPENAI
    openai_model: str = "text-embedding-3-large"
    sentence_transformer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_api_key: str | None = None
    fallback_to_local: bool = True


class EmbeddingService:
    """Wrapper exposing sync and async embedding interfaces."""

    def __init__(self, settings: EmbeddingSettings) -> None:
        self._settings = settings
        self._openai_client: Any | None = None
        self._openai_async_client: Any | None = None
        self._st_model: Any | None = None

    @property
    def settings(self) -> EmbeddingSettings:
        return self._settings

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings synchronously."""

        if not texts:
            return []

        if self._settings.provider is LLMProvider.OPENAI:
            try:
                return self._embed_with_openai_sync(texts)
            except Exception as exc:
                if self._settings.fallback_to_local:
                    logger.warning(
                        "openai embeddings unavailable; using sentence-transformer fallback",
                        extra={"error": str(exc)},
                    )
                    return self._embed_with_sentence_transformer(texts)
                raise

        return self._embed_with_sentence_transformer(texts)

    async def embed_async(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings asynchronously."""

        if not texts:
            return []

        if self._settings.provider is LLMProvider.OPENAI:
            try:
                return await self._embed_with_openai_async(texts)
            except Exception as exc:
                if self._settings.fallback_to_local:
                    logger.warning(
                        "openai embeddings unavailable; using sentence-transformer fallback",
                        extra={"error": str(exc)},
                    )
                    return await self._embed_with_sentence_transformer_async(texts)
                raise

        return await self._embed_with_sentence_transformer_async(texts)

    def _embed_with_openai_sync(self, texts: Sequence[str]) -> list[list[float]]:
        client = self._load_openai_client()
        response = client.embeddings.create(
            input=list(texts),
            model=self._settings.openai_model,
        )
        return [list(map(float, item.embedding)) for item in response.data]

    async def _embed_with_openai_async(self, texts: Sequence[str]) -> list[list[float]]:
        client = self._load_openai_async_client()
        response = await client.embeddings.create(
            input=list(texts),
            model=self._settings.openai_model,
        )
        return [list(map(float, item.embedding)) for item in response.data]

    def _embed_with_sentence_transformer(
        self, texts: Sequence[str]
    ) -> list[list[float]]:
        model = self._load_sentence_transformer()
        vectors = model.encode(texts, convert_to_numpy=False, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]

    async def _embed_with_sentence_transformer_async(
        self, texts: Sequence[str]
    ) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        model = self._load_sentence_transformer()
        vectors = await loop.run_in_executor(
            None,
            lambda: model.encode(
                texts, convert_to_numpy=False, normalize_embeddings=True
            ),
        )
        return [list(map(float, vector)) for vector in vectors]

    def _load_openai_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - guard for missing dependency
            raise RuntimeError(
                "openai package is required for OpenAI embeddings"
            ) from exc

        if not self._settings.openai_api_key:
            raise RuntimeError("openai_api_key must be provided for OpenAI embeddings")

        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=self._settings.openai_api_key)
        return self._openai_client

    def _load_openai_async_client(self) -> Any:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - guard for missing dependency
            raise RuntimeError(
                "openai package is required for OpenAI embeddings"
            ) from exc

        if not self._settings.openai_api_key:
            raise RuntimeError("openai_api_key must be provided for OpenAI embeddings")

        if self._openai_async_client is None:
            self._openai_async_client = AsyncOpenAI(
                api_key=self._settings.openai_api_key
            )
        return self._openai_async_client

    def _load_sentence_transformer(self) -> Any:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - guard for missing dependency
            raise RuntimeError(
                "sentence-transformers package is required for offline embeddings"
            ) from exc

        if self._st_model is None:
            logger.info(
                "loading sentence-transformer model",
                extra={"model": self._settings.sentence_transformer_model},
            )
            self._st_model = SentenceTransformer(
                self._settings.sentence_transformer_model
            )
        return self._st_model
