"""SQLModel declarative models for core entities."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, List
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, String, Text, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

from chatbot.core.domain import ChannelType


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def created_at_field() -> Any:
    return Field(
        default_factory=_utcnow,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )


def updated_at_field() -> Any:
    return Field(
        default_factory=_utcnow,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


class UUIDPrimaryKey(SQLModel, table=False):
    """Mixin providing a UUID primary key."""

    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)


class Tenant(UUIDPrimaryKey, table=True):
    """Top-level tenant grouping brands and channels."""

    __tablename__ = "tenants"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    name: str = Field(sa_column=Column(String(length=200), nullable=False, unique=True))
    timezone: str = Field(sa_column=Column(String(length=64), nullable=False, default="UTC"))
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSON, nullable=True),
    )

    brands: List["Brand"] = Relationship(
        back_populates="tenant", sa_relationship_kwargs={"cascade": "all,delete"}
    )
    conversations: List["Conversation"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )


class Brand(UUIDPrimaryKey, table=True):
    """Brand belonging to a tenant."""

    __tablename__ = "brands"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    tenant_id: UUID = Field(
        foreign_key="tenants.id",
        nullable=False,
    )
    name: str = Field(sa_column=Column(String(length=200), nullable=False))
    slug: str = Field(sa_column=Column(String(length=200), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    language: str = Field(sa_column=Column(String(length=16), nullable=False, default="en"))

    tenant: Tenant | None = Relationship(back_populates="brands")
    channels: List["ChannelConfig"] = Relationship(
        back_populates="brand",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )
    persona_profiles: List["PersonaProfile"] = Relationship(
        back_populates="brand",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )
    conversations: List["Conversation"] = Relationship(
        back_populates="brand",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )
    knowledge_sources: List["KnowledgeSource"] = Relationship(
        back_populates="brand",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )
    automation_rules: List["AutomationRule"] = Relationship(
        back_populates="brand",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )

    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_brand_tenant_slug"),)


class ChannelConfig(UUIDPrimaryKey, table=True):
    """Configuration for an external messaging channel."""

    __tablename__ = "channel_configs"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    channel_type: ChannelType = Field(sa_column=Column(String(length=32), nullable=False))
    display_name: str = Field(sa_column=Column(String(length=120), nullable=False))
    credentials: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    is_active: bool = Field(default=True, nullable=False)

    brand: Brand | None = Relationship(back_populates="channels")
    conversations: List["Conversation"] = Relationship(
        back_populates="channel",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )


class PersonaProfile(UUIDPrimaryKey, table=True):
    """Persona prompts and styling instructions for a brand."""

    __tablename__ = "persona_profiles"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    name: str = Field(sa_column=Column(String(length=120), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    prompt_template: str = Field(sa_column=Column(Text, nullable=False))
    language: str = Field(sa_column=Column(String(length=16), nullable=False, default="en"))
    tone_guidelines: list[str] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    brand: Brand | None = Relationship(back_populates="persona_profiles")


class Conversation(UUIDPrimaryKey, table=True):
    """Conversation lifecycle across channels."""

    __tablename__ = "conversations"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False)
    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    channel_config_id: UUID | None = Field(
        default=None,
        foreign_key="channel_configs.id",
        nullable=True,
    )
    customer_id: str = Field(sa_column=Column(String(length=120), nullable=False))
    status: str = Field(sa_column=Column(String(length=32), nullable=False, default="open"))
    last_message_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    tenant: Tenant | None = Relationship(back_populates="conversations")
    brand: Brand | None = Relationship(back_populates="conversations")
    channel: ChannelConfig | None = Relationship(back_populates="conversations")
    messages: List["MessageLog"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageLog(UUIDPrimaryKey, table=True):
    """Individual inbound/outbound messages within a conversation."""

    __tablename__ = "message_logs"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    conversation_id: UUID = Field(foreign_key="conversations.id", nullable=False, index=True)
    direction: MessageDirection = Field(sa_column=Column(String(length=16), nullable=False))
    role: str = Field(sa_column=Column(String(length=32), nullable=False, default="user"))
    sender_id: str | None = Field(
        default=None,
        sa_column=Column(String(length=120), nullable=True),
    )
    message_type: str = Field(
        sa_column=Column(String(length=32), nullable=False, default="text"),
    )
    content: str = Field(sa_column=Column(Text, nullable=False))
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSON, nullable=True),
    )

    conversation: Conversation | None = Relationship(back_populates="messages")


class KnowledgeSourceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class KnowledgeSource(UUIDPrimaryKey, table=True):
    """Source documents used to populate the vector store."""

    __tablename__ = "knowledge_sources"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    source_uri: str = Field(sa_column=Column(Text, nullable=False))
    asset_type: str = Field(sa_column=Column(String(length=64), nullable=False, default="document"))
    checksum: str = Field(sa_column=Column(String(length=128), nullable=False))
    status: KnowledgeSourceStatus = Field(
        default=KnowledgeSourceStatus.PENDING,
        sa_column=Column(
            String(length=16),
            nullable=False,
            default=KnowledgeSourceStatus.PENDING.value,
        ),
    )
    failure_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSON, nullable=True),
    )

    brand: Brand | None = Relationship(back_populates="knowledge_sources")
    chunks: List["KnowledgeChunk"] = Relationship(
        back_populates="source",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )

    __table_args__ = (
        UniqueConstraint("brand_id", "checksum", name="uq_knowledge_source_brand_checksum"),
    )


class KnowledgeChunk(UUIDPrimaryKey, table=True):
    """Individual chunk records referencing the vector store."""

    __tablename__ = "knowledge_chunks"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    knowledge_source_id: UUID = Field(foreign_key="knowledge_sources.id", nullable=False)
    chunk_id: str = Field(sa_column=Column(String(length=64), nullable=False))
    score: float | None = Field(default=None, nullable=True)
    content: str = Field(sa_column=Column(Text, nullable=False))
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSON, nullable=True),
    )
    vector_external_id: str | None = Field(
        default=None,
        sa_column=Column(String(length=128), nullable=True),
    )

    source: KnowledgeSource | None = Relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("knowledge_source_id", "chunk_id", name="uq_chunk_source_reference"),
    )


class AutomationRule(UUIDPrimaryKey, table=True):
    """Automation action triggers defined per brand."""

    __tablename__ = "automation_rules"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    name: str = Field(sa_column=Column(String(length=120), nullable=False))
    trigger_event: str = Field(sa_column=Column(String(length=64), nullable=False))
    condition: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    action_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    is_active: bool = Field(default=True, nullable=False)

    brand: Brand | None = Relationship(back_populates="automation_rules")


metadata = SQLModel.metadata
