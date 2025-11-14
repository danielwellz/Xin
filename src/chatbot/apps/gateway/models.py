"""Data transfer objects and mapping helpers for channel gateway."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from chatbot.core.domain import ChannelType, InboundMessage


@dataclass(slots=True)
class ProviderInboundEnvelope:
    """Raw payload received from a messaging provider."""

    event_id: str
    tenant_id: UUID
    brand_id: UUID
    channel_id: UUID
    sender_id: str
    conversation_id: UUID | None
    content: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    locale: str | None = None
    metadata: Mapping[str, Any] | None = None
    attachments: Sequence[Mapping[str, Any]] = field(default_factory=list)

    def to_inbound_message(self, *, channel_type: ChannelType) -> InboundMessage:
        """Translate the provider envelope into the shared inbound message format."""

        conversation_id = self.conversation_id or uuid4()
        return InboundMessage(
            id=uuid4(),
            tenant_id=self.tenant_id,
            brand_id=self.brand_id,
            channel_id=self.channel_id,
            conversation_id=conversation_id,
            sender_id=self.sender_id,
            content=self.content,
            received_at=self.occurred_at,
            locale=self.locale,
            attachments=list(self.attachments),
            metadata=self.metadata,
        )


@dataclass(slots=True)
class SignatureContext:
    """Contextual information required for signature validation."""

    signature: str
    secret: str
    payload: bytes
    timestamp: str | None = None
