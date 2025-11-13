"""Pydantic schemas for the admin/API surface."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from chatbot.core.domain import ChannelType
from chatbot.core.db.models import (
    ChannelSecretPurpose,
    KnowledgeAssetVisibility,
    KnowledgeSourceStatus,
    IngestionJobStatus,
    AutomationJobStatus,
    PolicyStatus,
)


class EmbedConfigResponse(BaseModel):
    tenant_id: UUID
    handshake_salt: str
    token_ttl_seconds: int
    theme: dict[str, Any] | None = None
    widget_options: dict[str, Any] | None = None


class TenantBase(BaseModel):
    name: str
    timezone: str = "UTC"
    metadata: dict[str, Any] | None = None


class TenantCreateRequest(TenantBase):
    embed_theme: dict[str, Any] | None = None
    widget_options: dict[str, Any] | None = None


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    timezone: str | None = None
    metadata: dict[str, Any] | None = None
    embed_theme: dict[str, Any] | None = None
    widget_options: dict[str, Any] | None = None


class TenantResponse(TenantBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    embed_config: EmbedConfigResponse | None = None


class ChannelCreateRequest(BaseModel):
    tenant_id: UUID
    brand_name: str
    channel_type: ChannelType
    display_name: str
    credentials: dict[str, Any] | None = None
    secret_credentials: dict[str, str] | None = None


class ChannelResponse(BaseModel):
    id: UUID
    brand_id: UUID
    channel_type: ChannelType
    display_name: str
    is_active: bool
    credentials: dict[str, Any] | None = None
    hmac_secret: str | None = Field(
        default=None, description="Only returned once upon creation."
    )


class PolicyVersionResponse(BaseModel):
    id: UUID
    version: int
    status: PolicyStatus
    summary: str | None = None
    created_at: datetime
    published_at: datetime | None = None


class PolicyDraftRequest(BaseModel):
    tenant_id: UUID
    summary: str | None = None
    policy_json: dict[str, Any]


class PolicyPublishRequest(BaseModel):
    version_id: UUID
    notes: str | None = None


class PolicyRollbackRequest(BaseModel):
    target_version: int
    notes: str | None = None


class PolicyDiffResponse(BaseModel):
    version: int
    previous_version: int | None = None
    diff_json: dict[str, Any]
    created_at: datetime
    created_by: str
    notes: str | None = None


class RetrievalConfigResponse(BaseModel):
    tenant_id: UUID
    hybrid_weight: float
    min_score: float
    max_documents: int
    context_budget_tokens: int
    filters: dict[str, Any] | None = None
    fallback_llm: str | None = None
    updated_at: datetime


class RetrievalConfigRequest(BaseModel):
    hybrid_weight: float | None = None
    min_score: float | None = None
    max_documents: int | None = None
    context_budget_tokens: int | None = None
    filters: dict[str, Any] | None = None
    fallback_llm: str | None = None


class KnowledgeAssetResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    brand_id: UUID
    knowledge_source_id: UUID
    title: str
    tags: list[str]
    visibility: KnowledgeAssetVisibility
    status: KnowledgeSourceStatus
    created_at: datetime
    updated_at: datetime


class KnowledgeAssetUploadRequest(BaseModel):
    tenant_id: UUID
    brand_id: UUID
    filename: str
    content_type: str
    data_base64: str
    tags: list[str] | None = None
    visibility: KnowledgeAssetVisibility | None = None


class IngestionJobResponse(BaseModel):
    id: UUID
    knowledge_source_id: UUID
    tenant_id: UUID
    brand_id: UUID
    status: IngestionJobStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    total_chunks: int | None = None
    processed_chunks: int | None = None
    failure_reason: str | None = None
    logs: list[dict[str, Any]] | None = None


class IngestionJobCreateRequest(BaseModel):
    tenant_id: UUID
    brand_id: UUID
    knowledge_source_id: UUID
    reason: str | None = None


class IngestionJobActionRequest(BaseModel):
    reason: str | None = None


class RetrievalDiagnosticsRequest(BaseModel):
    tenant_id: UUID
    brand_id: UUID
    message: str
    channel_id: UUID | None = None
    max_documents: int | None = None


class RetrievalDiagnosticsResponse(BaseModel):
    query: str
    documents: list[dict[str, Any]]
    applied_config: RetrievalConfigResponse


class AutomationRuleBase(BaseModel):
    tenant_id: UUID
    brand_id: UUID
    name: str
    trigger_type: str = "event"
    trigger_event: str
    schedule_expression: str | None = None
    condition: dict[str, Any] | None = None
    action_type: str = "webhook"
    action_payload: dict[str, Any] = Field(default_factory=dict)
    throttle_seconds: int = 0
    max_retries: int = 3


class AutomationRuleCreateRequest(AutomationRuleBase):
    is_active: bool = True


class AutomationRuleUpdateRequest(BaseModel):
    name: str | None = None
    trigger_type: str | None = None
    trigger_event: str | None = None
    schedule_expression: str | None = None
    condition: dict[str, Any] | None = None
    action_type: str | None = None
    action_payload: dict[str, Any] | None = None
    throttle_seconds: int | None = None
    max_retries: int | None = None
    is_active: bool | None = None


class AutomationRuleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    brand_id: UUID
    name: str
    trigger_type: str
    trigger_event: str
    schedule_expression: str | None
    condition: dict[str, Any] | None
    action_type: str
    action_payload: dict[str, Any]
    throttle_seconds: int
    max_retries: int
    is_active: bool
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AutomationJobResponse(BaseModel):
    id: UUID
    rule_id: UUID
    tenant_id: UUID
    brand_id: UUID
    status: AutomationJobStatus
    attempts: int
    scheduled_for: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    payload: dict[str, Any]
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AutomationJobActionRequest(BaseModel):
    reason: str | None = None


class AutomationTestRequest(BaseModel):
    rule: AutomationRuleCreateRequest
    sample_payload: dict[str, Any] | None = None


class TokenIssueRequest(BaseModel):
    subject: str
    roles: list[str]
    tenant_id: UUID | None = None
    ttl_seconds: int | None = Field(default=None, ge=60, le=86400)


class TokenIssueResponse(BaseModel):
    token: str
    expires_at: datetime


class EmbedSnippetResponse(BaseModel):
    tenant_id: UUID
    snippet: str


class AuditLogEntryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    created_at: datetime
    tenant_id: UUID | None = None
    actor: str
    action: str
    target_type: str
    target_id: str
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")
