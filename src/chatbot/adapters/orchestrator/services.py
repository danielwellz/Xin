"""Domain services powering the orchestrator FastAPI application."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, cast
from uuid import UUID, uuid4

from redis import Redis
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel import Session, select

from chatbot.core.config import AppSettings
from chatbot.core.db import models as db_models
from chatbot.core.db.models import KnowledgeSourceStatus, MessageDirection
from chatbot.core.storage import ObjectStorageClient
from chatbot.utils.tracing import generate_trace_id
from chatbot.rag.embeddings import EmbeddingService
from chatbot.rag.retrieval import retrieve_context
from chatbot.rag.vector_store import VectorDocument, VectorStore

from . import schemas

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class ProcessedInbound:
    """Result structure returned by ``OrchestratorService``."""

    conversation_id: UUID
    outbound_message_id: UUID
    outbound_content: str
    persona_prompt: str | None
    trace_id: str
    context: Sequence[VectorDocument]

    def to_response(self) -> schemas.InboundMessageResponse:
        """Render the dataclass as a response model."""

        snippets = []
        for document in self.context:
            raw_score = document.metadata.get("score")
            score = float(raw_score) if raw_score is not None else None
            snippets.append(
                schemas.ContextSnippet(
                    id=document.id,
                    text=document.text,
                    score=score,
                    metadata=document.metadata,
                )
            )
        return schemas.InboundMessageResponse(
            conversation_id=self.conversation_id,
            outbound=schemas.OutboundMessagePayload(
                message_id=self.outbound_message_id,
                content=self.outbound_content,
                persona_prompt=self.persona_prompt,
                trace_id=self.trace_id,
                context=snippets,
            ),
        )


class GuardrailViolation(RuntimeError):
    """Raised when a generated message fails guardrail checks."""


class GuardrailService:
    """Very lightweight guardrail implementation to block obviously unsafe content."""

    def __init__(self, *, banned_terms: Iterable[str] | None = None) -> None:
        terms = {term.lower() for term in (banned_terms or {"kill", "suicide", "bomb"})}
        self._banned_terms = terms

    def validate(self, message: str) -> None:
        """Raise ``GuardrailViolation`` if the message contains a banned term."""

        lowered = message.lower()
        for term in self._banned_terms:
            if term in lowered:
                raise GuardrailViolation(f"response contains banned term: {term}")


class LLMClient:
    """Simplistic LLM facade that can be swapped out for real providers."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def generate_reply(
        self,
        *,
        persona_prompt: str | None,
        message: str,
        history: Sequence[db_models.MessageLog],
        context: Sequence[VectorDocument],
    ) -> str:
        """Craft a templated response blending persona, history, and context.

        In a production deployment this method would call an external LLM API.
        For local development and tests we synthesise a deterministic response
        so behaviour can be asserted without external dependencies.
        """

        persona_block = persona_prompt or "You are a helpful assistant."
        history_lines = [f"{item.role}: {item.content}" for item in history[-5:]]
        context_snippets = [doc.text for doc in context[:3]]

        reply_lines = [
            persona_block,
            "",
            "Recent conversation:",
            *(history_lines or ["(no prior history)"]),
            "",
            "Relevant knowledge:",
            *(context_snippets or ["(no matching snippets found)"]),
            "",
            f"Assistant: Based on the above, here's a helpful answer regarding '{message}'.",
        ]
        return "\n".join(reply_lines)


class ContextService:
    """Wrapper handling retrieval of contextual snippets for a message."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None,
        vector_store: VectorStore | None,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store

    def retrieve(
        self,
        *,
        tenant_id: UUID,
        brand_id: UUID,
        message: str,
        top_k: int = 5,
    ) -> Sequence[VectorDocument]:
        if not message.strip():
            return []
        if self._embedding_service is None or self._vector_store is None:
            logger.debug("context retrieval disabled; missing embedding/vector store")
            return []
        try:
            return retrieve_context(
                tenant_id=tenant_id,
                brand_id=brand_id,
                message=message,
                embedding_service=self._embedding_service,
                vector_store=self._vector_store,
                top_k=top_k,
            )
        except Exception:  # pragma: no cover - defensive logging path
            logger.exception("failed to retrieve context snippets")
            return []


class ConversationService:
    """Encapsulates persistence operations for conversations and messages."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    def ensure_conversation(
        self,
        payload: schemas.InboundMessageRequest,
    ) -> db_models.Conversation:
        conversation = self._session.get(db_models.Conversation, payload.conversation_id)
        if conversation is None:
            conversation = db_models.Conversation(
                id=payload.conversation_id,
                tenant_id=payload.tenant_id,
                brand_id=payload.brand_id,
                channel_config_id=payload.channel_id,
                customer_id=payload.sender_id,
                last_message_at=payload.received_at,
            )
            self._session.add(conversation)
        else:
            conversation.last_message_at = payload.received_at
        return conversation

    def log_inbound(
        self,
        conversation: db_models.Conversation,
        payload: schemas.InboundMessageRequest,
        *,
        trace_id: str,
    ) -> db_models.MessageLog:
        metadata = {
            "trace_id": trace_id,
            "attachments": [attachment.model_dump() for attachment in payload.attachments],
            "metadata": payload.metadata or {},
        }
        log = db_models.MessageLog(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            role="user",
            sender_id=payload.sender_id,
            content=payload.content,
            metadata_json=metadata,
        )
        self._session.add(log)
        conversation.last_message_at = payload.received_at
        return log

    def log_outbound(
        self,
        conversation: db_models.Conversation,
        *,
        content: str,
        persona_prompt: str | None,
        context: Sequence[VectorDocument],
        trace_id: str,
    ) -> db_models.MessageLog:
        metadata = {
            "trace_id": trace_id,
            "persona_prompt": persona_prompt,
            "context": [
                {"id": doc.id, "text": doc.text, "metadata": doc.metadata} for doc in context
            ],
        }
        log = db_models.MessageLog(
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            role="assistant",
            content=content,
            metadata_json=metadata,
        )
        self._session.add(log)
        conversation.last_message_at = datetime.now(tz=UTC)
        return log

    def get_history(self, conversation_id: UUID, *, limit: int = 20) -> list[db_models.MessageLog]:
        statement = (
            select(db_models.MessageLog)
            .where(db_models.MessageLog.conversation_id == conversation_id)
            .order_by(asc("created_at"))
        )
        results: list[db_models.MessageLog] = list(self._session.exec(statement).all())
        if limit:
            return list(results[-limit:])
        return results

    def get_active_persona_prompt(self, brand_id: UUID) -> str | None:
        statement = (
            select(db_models.PersonaProfile)
            .where(db_models.PersonaProfile.brand_id == brand_id)
            .order_by(desc("created_at"))
        )
        persona = self._session.exec(statement).first()
        if persona is None:
            return None
        return persona.prompt_template

    def get_brand(self, brand_id: UUID) -> db_models.Brand:
        brand = self._session.get(db_models.Brand, brand_id)
        if brand is None:
            raise NoResultFound(f"brand {brand_id} not found")
        return brand

    def get_channel_config(self, channel_id: UUID) -> db_models.ChannelConfig:
        channel = self._session.get(db_models.ChannelConfig, channel_id)
        if channel is None:
            raise NoResultFound(f"channel {channel_id} not found")
        return channel

    def fetch_conversation(self, conversation_id: UUID) -> db_models.Conversation:
        conversation = self._session.get(db_models.Conversation, conversation_id)
        if conversation is None:
            raise NoResultFound(f"conversation {conversation_id} not found")
        return conversation


class OrchestratorService:
    """Primary use-case façade for processing inbound messages."""

    def __init__(
        self,
        conversation_service: ConversationService,
        context_service: ContextService,
        llm_client: LLMClient,
        guardrail_service: GuardrailService,
        redis_client: Redis | None = None,
        *,
        outbound_stream: str = "outbound:messages",
    ) -> None:
        self._conversation_service = conversation_service
        self._context_service = context_service
        self._llm_client = llm_client
        self._guardrail_service = guardrail_service
        self._redis = redis_client
        self._stream = outbound_stream

    def process_inbound(self, payload: schemas.InboundMessageRequest) -> ProcessedInbound:
        """Process an inbound message end-to-end."""

        session = self._conversation_service.session
        trace_id = generate_trace_id()

        conversation = self._conversation_service.ensure_conversation(payload)
        self._conversation_service.log_inbound(conversation, payload, trace_id=trace_id)
        channel = self._conversation_service.get_channel_config(payload.channel_id)

        history = self._conversation_service.get_history(payload.conversation_id)
        context = self._context_service.retrieve(
            tenant_id=payload.tenant_id,
            brand_id=payload.brand_id,
            message=payload.content,
        )
        persona_prompt = self._conversation_service.get_active_persona_prompt(payload.brand_id)
        reply = self._llm_client.generate_reply(
            persona_prompt=persona_prompt,
            message=payload.content,
            history=history,
            context=context,
        )
        self._guardrail_service.validate(reply)

        conversation = self._conversation_service.ensure_conversation(payload)
        outbound = self._conversation_service.log_outbound(
            conversation,
            content=reply,
            persona_prompt=persona_prompt,
            context=context,
            trace_id=trace_id,
        )

        self._publish_outbound_message(
            outbound_log=outbound,
            conversation=conversation,
            channel=channel,
            content=reply,
            trace_id=trace_id,
            persona_prompt=persona_prompt,
            context=context,
        )

        return ProcessedInbound(
            conversation_id=payload.conversation_id,
            outbound_message_id=outbound.id,
            outbound_content=reply,
            persona_prompt=persona_prompt,
            trace_id=trace_id,
            context=context,
        )

    def _publish_outbound_message(
        self,
        *,
        outbound_log: db_models.MessageLog,
        conversation: db_models.Conversation,
        channel: db_models.ChannelConfig,
        content: str,
        trace_id: str,
        persona_prompt: str | None,
        context: Sequence[VectorDocument],
    ) -> None:
        if self._redis is None:
            logger.debug("skipping redis publish; client not configured")
            return

        metadata = {
            "trace_id": trace_id,
            "channel_type": channel.channel_type.value
            if hasattr(channel.channel_type, "value")
            else str(channel.channel_type),
            "persona_prompt": persona_prompt,
            "context": [
                {"id": doc.id, "text": doc.text, "metadata": doc.metadata} for doc in context
            ],
        }

        raw_payload = {
            "id": str(outbound_log.id),
            "tenant_id": str(conversation.tenant_id),
            "brand_id": str(conversation.brand_id),
            "channel_id": str(channel.id),
            "conversation_id": str(conversation.id),
            "content": content,
            "created_at": outbound_log.created_at.isoformat(),
            "metadata": json.dumps(metadata),
        }
        payload = cast(dict[Any, Any], raw_payload)
        try:
            self._redis.xadd(self._stream, payload)
        except Exception:  # pragma: no cover - redis failures should not crash requests
            logger.exception("failed to publish outbound message to redis stream")


@dataclass(slots=True)
class KnowledgeRegistrationResult:
    """Return type wrapping a registered knowledge source."""

    knowledge: db_models.KnowledgeSource
    tenant_id: UUID
    brand_id: UUID
    filename: str
    content_type: str
    source_uri: str
    should_enqueue: bool = True


class KnowledgeService:
    """Handles registration of brand knowledge uploads."""

    def __init__(self, session: Session, storage: ObjectStorageClient) -> None:
        self._session = session
        self._storage = storage

    def register_document(
        self,
        *,
        brand_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> KnowledgeRegistrationResult:
        brand = self._session.get(db_models.Brand, brand_id)
        if brand is None:
            raise NoResultFound(f"brand {brand_id} not found")

        checksum = sha256(data).hexdigest()
        existing = self._find_existing_knowledge(brand_id=brand_id, checksum=checksum, tolerate=True)
        if existing is not None:
            logger.info(
                "using existing knowledge source for duplicate upload",
                extra={"brand_id": str(brand_id), "knowledge_source_id": str(existing.id)},
            )
            return KnowledgeRegistrationResult(
                knowledge=existing,
                tenant_id=brand.tenant_id,
                brand_id=brand_id,
                filename=filename,
                content_type=content_type,
                source_uri=existing.source_uri,
                should_enqueue=False,
            )

        knowledge_id = uuid4()
        upload = self._storage.upload_document(
            tenant_id=brand.tenant_id,
            brand_id=brand_id,
            knowledge_id=knowledge_id,
            filename=filename,
            content_type=content_type,
            data=data,
        )

        knowledge = db_models.KnowledgeSource(
            id=knowledge_id,
            brand_id=brand_id,
            source_uri=upload.uri,
            asset_type=self._infer_asset_type(content_type),
            checksum=checksum,
            status=KnowledgeSourceStatus.PENDING,
            metadata_json={"filename": upload.filename, "storage_key": upload.key},
        )
        self._session.add(knowledge)
        try:
            self._session.flush()
        except IntegrityError:
            self._session.rollback()
            existing = self._find_existing_knowledge(brand_id=brand_id, checksum=checksum)
            logger.info(
                "using existing knowledge source for duplicate upload after flush",
                extra={"brand_id": str(brand_id), "knowledge_source_id": str(existing.id)},
            )
            return KnowledgeRegistrationResult(
                knowledge=existing,
                tenant_id=brand.tenant_id,
                brand_id=brand_id,
                filename=filename,
                content_type=content_type,
                source_uri=existing.source_uri,
                should_enqueue=False,
            )
        except Exception:
            self._session.rollback()
            raise

        return KnowledgeRegistrationResult(
            knowledge=knowledge,
            tenant_id=brand.tenant_id,
            brand_id=brand_id,
            filename=upload.filename,
            content_type=content_type,
            source_uri=upload.uri,
        )

    def _find_existing_knowledge(
        self, *, brand_id: UUID, checksum: str, tolerate: bool = False
    ) -> db_models.KnowledgeSource | None:
        statement = select(db_models.KnowledgeSource).where(
            db_models.KnowledgeSource.brand_id == brand_id,
            db_models.KnowledgeSource.checksum == checksum,
        )
        knowledge = self._session.exec(statement).first()
        if knowledge is None and not tolerate:
            raise NoResultFound("expected duplicate knowledge source to exist")
        return knowledge

    @staticmethod
    def _infer_asset_type(content_type: str) -> str:
        if "markdown" in content_type:
            return "markdown"
        if "pdf" in content_type:
            return "pdf"
        if "text" in content_type:
            return "text"
        return "document"


def convert_message_log(log: db_models.MessageLog) -> schemas.ConversationMessage:
    """Helper converting ``MessageLog`` records to API schema."""

    metadata = log.metadata_json if isinstance(log.metadata_json, dict) else None
    direction = log.direction.value if hasattr(log.direction, "value") else str(log.direction)
    return schemas.ConversationMessage(
        id=log.id,
        direction=direction,
        role=log.role,
        content=log.content,
        created_at=log.created_at,
        metadata=metadata,
    )
