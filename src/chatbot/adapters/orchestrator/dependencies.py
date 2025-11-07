"""Dependency wiring for the orchestrator FastAPI application."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis import Redis
from sqlalchemy.engine import Engine
from sqlmodel import Session

from chatbot.core.config import AppSettings
from chatbot.core.db.session import create_engine_from_settings, init_db
from chatbot.rag.embeddings import EmbeddingService, EmbeddingSettings
from chatbot.rag.vector_store import QdrantVectorStore, VectorStore

from .services import (
    ContextService,
    ConversationService,
    GuardrailService,
    KnowledgeService,
    LLMClient,
    OrchestratorService,
)

logger = logging.getLogger(__name__)


@lru_cache
def get_settings() -> AppSettings:
    """Return cached ``AppSettings`` instance."""

    return AppSettings.load()


@lru_cache
def get_engine() -> Engine:
    """Create (or reuse) the SQLModel engine."""

    settings = get_settings()
    engine = create_engine_from_settings(settings)
    init_db(engine)
    return engine


def get_session() -> Iterator[Session]:
    """Provide a SQLModel session per-request."""

    engine = get_engine()
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@lru_cache
def get_embedding_service() -> EmbeddingService | None:
    """Instantiate the embedding service when credentials are available."""

    settings = get_settings()
    openai_key = settings.openai.api_key
    if settings.llm.provider.value == "openai" and not openai_key:
        logger.info("skipping embedding service initialisation; openai api key missing")
        return None

    embed_settings = EmbeddingSettings(
        provider=settings.llm.provider,
        openai_model=settings.openai.embedding_model,
        openai_api_key=openai_key,
    )
    try:
        return EmbeddingService(embed_settings)
    except Exception:  # pragma: no cover - avoid crashing when optional deps are missing
        logger.exception("failed to initialise embedding service")
        return None


@lru_cache
def get_vector_store() -> VectorStore | None:
    """Create an instance of the Qdrant vector store."""

    settings = get_settings()
    try:
        return QdrantVectorStore(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            timeout=settings.qdrant.timeout_seconds,
        )
    except Exception:  # pragma: no cover - service may be unavailable in tests
        logger.exception("failed to initialise qdrant vector store")
        return None


@lru_cache
def get_redis_client() -> Redis | None:
    """Create a Redis client if the server is reachable."""

    settings = get_settings()
    try:
        client = Redis.from_url(settings.redis.url, decode_responses=True)
        client.ping()
        return client
    except Exception:  # pragma: no cover - redis may be unavailable
        logger.warning("redis unavailable; operating without stream publishing")
        return None


@lru_cache
def get_llm_client() -> LLMClient:
    """Return an LLM client wrapper."""

    settings = get_settings()
    return LLMClient(settings)


@lru_cache
def get_guardrail_service() -> GuardrailService:
    """Return the configured guardrail service."""

    return GuardrailService()


EmbeddingDep = Annotated[EmbeddingService | None, Depends(get_embedding_service)]
VectorStoreDep = Annotated[VectorStore | None, Depends(get_vector_store)]
SessionDep = Annotated[Session, Depends(get_session)]
RedisDep = Annotated[Redis | None, Depends(get_redis_client)]


def get_context_service(
    embedding_service: EmbeddingDep,
    vector_store: VectorStoreDep,
) -> ContextService:
    """Construct the context retrieval service."""

    return ContextService(embedding_service, vector_store)


def get_conversation_service(session: SessionDep) -> ConversationService:
    """Build a conversation service bound to the active DB session."""

    return ConversationService(session)


def get_orchestrator_service(
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    context_service: Annotated[ContextService, Depends(get_context_service)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    guardrail_service: Annotated[GuardrailService, Depends(get_guardrail_service)],
    redis_client: RedisDep,
) -> OrchestratorService:
    """Provide an orchestrator service instance for request handling."""

    return OrchestratorService(
        conversation_service,
        context_service,
        llm_client,
        guardrail_service,
        redis_client,
    )


def get_knowledge_service(
    session: SessionDep,
    redis_client: RedisDep,
) -> KnowledgeService:
    """Return the knowledge service for ingestion registration."""

    return KnowledgeService(session, redis_client)
