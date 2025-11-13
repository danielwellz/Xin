"""SQLModel declarative models for core entities."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, List, Optional
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


def deleted_at_field() -> Any:
    return Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
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
    timezone: str = Field(
        sa_column=Column(String(length=64), nullable=False, default="UTC")
    )
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
    embed_config: Optional["EmbedConfig"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"uselist": False, "cascade": "all,delete-orphan"},
    )
    policy_versions: List["PolicyVersion"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )
    audit_entries: List["AuditLogEntry"] = Relationship(
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
    language: str = Field(
        sa_column=Column(String(length=16), nullable=False, default="en")
    )

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

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_brand_tenant_slug"),
    )


class ChannelConfig(UUIDPrimaryKey, table=True):
    """Configuration for an external messaging channel."""

    __tablename__ = "channel_configs"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    channel_type: ChannelType = Field(
        sa_column=Column(String(length=32), nullable=False)
    )
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
    secrets: List["ChannelSecret"] = Relationship(
        back_populates="channel",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )


class ChannelSecretPurpose(str, Enum):
    HMAC = "hmac"
    API = "api"


class ChannelSecret(UUIDPrimaryKey, table=True):
    """Hashed channel secrets mirrored to the external vault."""

    __tablename__ = "channel_secrets"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    deleted_at: datetime | None = deleted_at_field()
    channel_id: UUID = Field(foreign_key="channel_configs.id", nullable=False)
    label: str = Field(sa_column=Column(String(length=120), nullable=False))
    purpose: ChannelSecretPurpose = Field(
        sa_column=Column(
            String(length=32), nullable=False, default=ChannelSecretPurpose.HMAC.value
        )
    )
    secret_hash: str = Field(sa_column=Column(String(length=128), nullable=False))
    secret_reference: str = Field(sa_column=Column(String(length=512), nullable=False))
    rotated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    channel: ChannelConfig | None = Relationship(back_populates="secrets")


class EmbedConfig(UUIDPrimaryKey, table=True):
    """Embed/widget configuration per tenant."""

    __tablename__ = "embed_configs"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    deleted_at: datetime | None = deleted_at_field()
    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False, unique=True)
    theme: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    widget_options: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    handshake_salt: str = Field(sa_column=Column(String(length=64), nullable=False))
    token_ttl_seconds: int = Field(default=900, ge=60, le=86400)

    tenant: Tenant | None = Relationship(back_populates="embed_config")


class PolicyStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PolicyVersion(UUIDPrimaryKey, table=True):
    """Versioned policy definitions."""

    __tablename__ = "policy_versions"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    deleted_at: datetime | None = deleted_at_field()
    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False)
    version: int = Field(default=1, ge=1, nullable=False)
    status: PolicyStatus = Field(
        sa_column=Column(
            String(length=32), nullable=False, default=PolicyStatus.DRAFT.value
        )
    )
    created_by: str = Field(sa_column=Column(String(length=120), nullable=False))
    summary: str | None = Field(
        default=None, sa_column=Column(String(length=255), nullable=True)
    )
    policy_json: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    published_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    tenant: Tenant | None = Relationship(back_populates="policy_versions")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "version", name="uq_policy_versions_tenant_version"
        ),
    )


class AuditLogEntry(UUIDPrimaryKey, table=True):
    """Immutable audit trail for privileged admin actions."""

    __tablename__ = "audit_log_entries"

    created_at: datetime = created_at_field()
    tenant_id: UUID | None = Field(
        foreign_key="tenants.id", default=None, nullable=True
    )
    actor: str = Field(sa_column=Column(String(length=120), nullable=False))
    actor_type: str = Field(
        sa_column=Column(String(length=64), nullable=False, default="user")
    )
    action: str = Field(sa_column=Column(String(length=120), nullable=False))
    target_type: str = Field(sa_column=Column(String(length=120), nullable=False))
    target_id: str = Field(sa_column=Column(String(length=120), nullable=False))
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    tenant: Tenant | None = Relationship(back_populates="audit_entries")


class PersonaProfile(UUIDPrimaryKey, table=True):
    """Persona prompts and styling instructions for a brand."""

    __tablename__ = "persona_profiles"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    name: str = Field(sa_column=Column(String(length=120), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    prompt_template: str = Field(sa_column=Column(Text, nullable=False))
    language: str = Field(
        sa_column=Column(String(length=16), nullable=False, default="en")
    )
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
    status: str = Field(
        sa_column=Column(String(length=32), nullable=False, default="open")
    )
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

    conversation_id: UUID = Field(
        foreign_key="conversations.id", nullable=False, index=True
    )
    direction: MessageDirection = Field(
        sa_column=Column(String(length=16), nullable=False)
    )
    role: str = Field(
        sa_column=Column(String(length=32), nullable=False, default="user")
    )
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
    asset_type: str = Field(
        sa_column=Column(String(length=64), nullable=False, default="document")
    )
    checksum: str = Field(sa_column=Column(String(length=128), nullable=False))
    status: KnowledgeSourceStatus = Field(
        default=KnowledgeSourceStatus.PENDING,
        sa_column=Column(
            String(length=16),
            nullable=False,
            default=KnowledgeSourceStatus.PENDING.value,
        ),
    )
    failure_reason: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSON, nullable=True),
    )

    brand: Brand | None = Relationship(back_populates="knowledge_sources")
    chunks: List["KnowledgeChunk"] = Relationship(
        back_populates="source",
        sa_relationship_kwargs={"cascade": "all,delete"},
    )
    asset: Optional["KnowledgeAsset"] = Relationship(
        back_populates="knowledge_source",
        sa_relationship_kwargs={"uselist": False},
    )

    __table_args__ = (
        UniqueConstraint(
            "brand_id", "checksum", name="uq_knowledge_source_brand_checksum"
        ),
    )


class KnowledgeChunk(UUIDPrimaryKey, table=True):
    """Individual chunk records referencing the vector store."""

    __tablename__ = "knowledge_chunks"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    knowledge_source_id: UUID = Field(
        foreign_key="knowledge_sources.id", nullable=False
    )
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
        UniqueConstraint(
            "knowledge_source_id", "chunk_id", name="uq_chunk_source_reference"
        ),
    )


class KnowledgeAssetVisibility(str, Enum):
    PRIVATE = "private"
    TENANT = "tenant"
    PUBLIC = "public"


class KnowledgeAsset(UUIDPrimaryKey, table=True):
    """Curated metadata describing a knowledge source."""

    __tablename__ = "knowledge_assets"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False)
    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    knowledge_source_id: UUID = Field(
        foreign_key="knowledge_sources.id", nullable=False, unique=True
    )
    title: str = Field(sa_column=Column(String(length=255), nullable=False))
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    visibility: KnowledgeAssetVisibility = Field(
        sa_column=Column(
            String(length=16),
            nullable=False,
            default=KnowledgeAssetVisibility.PRIVATE.value,
        )
    )
    status: KnowledgeSourceStatus = Field(
        sa_column=Column(
            String(length=16),
            nullable=False,
            default=KnowledgeSourceStatus.PENDING.value,
        )
    )
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSON, nullable=True),
    )

    knowledge_source: KnowledgeSource | None = Relationship(back_populates="asset")


class IngestionJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestionJob(UUIDPrimaryKey, table=True):
    """Tracks ingestion worker execution for a knowledge source."""

    __tablename__ = "ingestion_jobs"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    knowledge_source_id: UUID = Field(
        foreign_key="knowledge_sources.id", nullable=False, unique=True
    )
    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False)
    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    status: IngestionJobStatus = Field(
        sa_column=Column(
            String(length=16), nullable=False, default=IngestionJobStatus.PENDING.value
        )
    )
    created_by: str | None = Field(
        default=None, sa_column=Column(String(length=120), nullable=True)
    )
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    cancelled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    total_chunks: int | None = Field(default=None, nullable=True)
    processed_chunks: int | None = Field(default=None, nullable=True)
    failure_reason: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    logs: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )

    knowledge_source: KnowledgeSource | None = Relationship()
    tenant: Tenant | None = Relationship()
    brand: Brand | None = Relationship()


class AutomationRule(UUIDPrimaryKey, table=True):
    """Automation action triggers defined per brand."""

    __tablename__ = "automation_rules"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False)
    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    name: str = Field(sa_column=Column(String(length=120), nullable=False))
    trigger_event: str = Field(sa_column=Column(String(length=64), nullable=False))
    trigger_type: str = Field(
        sa_column=Column(String(length=32), nullable=False, default="event")
    )
    schedule_expression: str | None = Field(
        default=None, sa_column=Column(String(length=120), nullable=True)
    )
    condition: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    action_type: str = Field(
        sa_column=Column(String(length=32), nullable=False, default="webhook")
    )
    action_payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    throttle_seconds: int = Field(default=0, nullable=False)
    max_retries: int = Field(default=3, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    last_run_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    paused_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    brand: Brand | None = Relationship(back_populates="automation_rules")
    tenant: Tenant | None = Relationship()


class AutomationJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutomationJob(UUIDPrimaryKey, table=True):
    """Execution record for an automation rule."""

    __tablename__ = "automation_jobs"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    rule_id: UUID = Field(foreign_key="automation_rules.id", nullable=False)
    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False)
    brand_id: UUID = Field(foreign_key="brands.id", nullable=False)
    status: AutomationJobStatus = Field(
        sa_column=Column(
            String(length=16), nullable=False, default=AutomationJobStatus.PENDING.value
        )
    )
    attempts: int = Field(default=0, nullable=False)
    scheduled_for: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    started_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    failure_reason: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    rule: AutomationRule | None = Relationship()
    tenant: Tenant | None = Relationship()
    brand: Brand | None = Relationship()


class AutomationAudit(UUIDPrimaryKey, table=True):
    """Audit entries for automation rule lifecycle."""

    __tablename__ = "automation_audit"

    created_at: datetime = created_at_field()
    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False)
    rule_id: UUID = Field(foreign_key="automation_rules.id", nullable=False)
    actor: str = Field(sa_column=Column(String(length=120), nullable=False))
    action: str = Field(sa_column=Column(String(length=120), nullable=False))
    metadata_json: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

    tenant: Tenant | None = Relationship()
    rule: AutomationRule | None = Relationship()


class PolicySnapshot(UUIDPrimaryKey, table=True):
    """Historical diff for a policy version."""

    __tablename__ = "policy_snapshots"

    created_at: datetime = created_at_field()
    policy_version_id: UUID = Field(foreign_key="policy_versions.id", nullable=False)
    previous_version: int | None = Field(default=None, nullable=True)
    diff_json: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    created_by: str = Field(sa_column=Column(String(length=120), nullable=False))
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    policy_version: PolicyVersion | None = Relationship()


class RetrievalConfig(UUIDPrimaryKey, table=True):
    """Per-tenant retrieval controls."""

    __tablename__ = "retrieval_configs"

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()

    tenant_id: UUID = Field(foreign_key="tenants.id", nullable=False, unique=True)
    hybrid_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    max_documents: int = Field(default=5, ge=1, le=50)
    context_budget_tokens: int = Field(default=1200, ge=100, le=4000)
    filters: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    fallback_llm: str | None = Field(
        default=None, sa_column=Column(String(length=64), nullable=True)
    )

    tenant: Tenant | None = Relationship()


metadata = SQLModel.metadata
