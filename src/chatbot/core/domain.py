"""Domain data structures shared across services."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class ChannelType(str, Enum):
    """Supported messaging channels."""

    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB = "web"


@dataclass(slots=True)
class Tenant:
    """A logical tenant in the multi-tenant platform."""

    id: UUID
    name: str
    timezone: str
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class BrandProfile:
    """Brand configuration owned by a tenant."""

    id: UUID
    tenant_id: UUID
    name: str
    persona: str
    description: str | None = None
    language: str = "en"
    tone_guidelines: Sequence[str] = field(default_factory=list)
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class Channel:
    """Configured messaging channel for a brand."""

    id: UUID
    brand_id: UUID
    type: ChannelType
    display_name: str
    is_active: bool = True
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class InboundMessage:
    """Normalized payload propagated from channel adapters."""

    id: UUID
    tenant_id: UUID
    brand_id: UUID
    channel_id: UUID
    conversation_id: UUID
    sender_id: str
    content: str
    received_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    locale: str | None = None
    attachments: Sequence[Mapping[str, Any]] = field(default_factory=list)
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class OutboundResponse:
    """Response emitted by the orchestrator to be delivered to end users."""

    id: UUID
    tenant_id: UUID
    brand_id: UUID
    channel_id: UUID
    conversation_id: UUID
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    persona_applied: str | None = None
    confidence: float | None = None
    metadata: Mapping[str, Any] | None = None
    attachments: Sequence[Mapping[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class KnowledgeAsset:
    """Represents a source document or artifact used for retrieval-augmented generation."""

    id: UUID
    tenant_id: UUID
    brand_id: UUID
    source_uri: str
    asset_type: str
    checksum: str
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    tags: Sequence[str] = field(default_factory=list)
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class ActionRequest:
    """Structured action emitted by the LLM for downstream automation."""

    id: UUID = field(default_factory=uuid4)
    conversation_id: UUID | None = None
    action_type: str = "generic"
    payload: Mapping[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    requires_approval: bool = False
