from __future__ import annotations

import pytest

from chatbot.core.config import LLMProvider
from chatbot.rag.embeddings import EmbeddingService, EmbeddingSettings


pytestmark = pytest.mark.unit


class _StubModel:
    def encode(self, texts, convert_to_numpy=False, normalize_embeddings=True):  # noqa: ANN001, ANN202
        return [[float(len(text))] for text in texts]


def test_openai_fallbacks_to_sentence_transformer(monkeypatch):
    def _raise_openai(_: EmbeddingService):  # noqa: ANN001
        raise RuntimeError("openai disabled")

    monkeypatch.setattr(EmbeddingService, "_load_openai_client", _raise_openai)
    monkeypatch.setattr(EmbeddingService, "_load_openai_async_client", _raise_openai)
    monkeypatch.setattr(
        EmbeddingService, "_load_sentence_transformer", lambda self: _StubModel()
    )

    service = EmbeddingService(
        EmbeddingSettings(
            provider=LLMProvider.OPENAI, openai_api_key=None, fallback_to_local=True
        )
    )

    vectors = service.embed(["hello world"])
    assert vectors == [[11.0]]


@pytest.mark.asyncio
async def test_openai_async_fallback(monkeypatch):
    def _raise_openai(_: EmbeddingService):  # noqa: ANN001
        raise RuntimeError("openai disabled")

    monkeypatch.setattr(EmbeddingService, "_load_openai_client", _raise_openai)
    monkeypatch.setattr(EmbeddingService, "_load_openai_async_client", _raise_openai)
    monkeypatch.setattr(
        EmbeddingService, "_load_sentence_transformer", lambda self: _StubModel()
    )

    service = EmbeddingService(
        EmbeddingSettings(
            provider=LLMProvider.OPENAI, openai_api_key=None, fallback_to_local=True
        )
    )

    vectors = await service.embed_async(["xin"])
    assert vectors == [[3.0]]


def test_openai_without_fallback_raises(monkeypatch):
    def _raise(_: EmbeddingService):  # noqa: ANN001
        raise RuntimeError("no api key")

    monkeypatch.setattr(EmbeddingService, "_load_openai_client", _raise)

    service = EmbeddingService(
        EmbeddingSettings(
            provider=LLMProvider.OPENAI, openai_api_key=None, fallback_to_local=False
        )
    )

    with pytest.raises(RuntimeError, match="no api key"):
        service.embed(["xin"])
