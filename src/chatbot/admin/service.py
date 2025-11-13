"""Domain services for the admin/onboarding API."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from prometheus_client import Counter, Gauge
from redis import Redis
from sqlmodel import Session, select

from chatbot.admin import schemas
from chatbot.core.db import models
from chatbot.core.logging import get_logger
from chatbot.core.storage import ObjectStorageClient

ADMIN_ACTION_COUNTER = Counter(
    "admin_actions_total",
    "Total admin mutations handled.",
    ["action", "result"],
)
INGESTION_JOBS_GAUGE = Gauge(
    "ingestion_jobs_inflight",
    "Number of ingestion jobs currently running per tenant.",
    ["tenant_id"],
)

TENANT_CACHE_TTL_SECONDS = 900
CHANNEL_CACHE_TTL_SECONDS = 900

logger = get_logger("admin.service")


class AdminService:
    """Implements the onboarding/admin workflows."""

    def __init__(
        self,
        session: Session,
        storage_client: ObjectStorageClient,
        redis_client: Redis | None,
    ) -> None:
        self._session = session
        self._storage = storage_client
        self._redis = redis_client

    # Tenant operations --------------------------------------------------

    def create_tenant(
        self,
        request: schemas.TenantCreateRequest,
        *,
        actor: str,
    ) -> models.Tenant:
        if self._session.exec(
            select(models.Tenant).where(models.Tenant.name == request.name)
        ).first():
            raise ValueError("tenant_name_conflict")

        tenant = models.Tenant(
            name=request.name,
            timezone=request.timezone,
            metadata_json=request.metadata,
        )
        self._session.add(tenant)
        self._session.flush()

        embed = models.EmbedConfig(
            tenant_id=tenant.id,
            theme=request.embed_theme,
            widget_options=request.widget_options,
            handshake_salt=secrets.token_hex(16),
            token_ttl_seconds=900,
        )
        tenant.embed_config = embed
        self._session.add(embed)

        policy = models.PolicyVersion(
            tenant_id=tenant.id,
            version=1,
            status=models.PolicyStatus.DRAFT,
            created_by=actor,
            summary="Initial scaffold",
            policy_json={"responses": [], "actions": []},
        )
        self._session.add(policy)
        self._session.flush()

        self._record_audit(
            actor=actor,
            action="tenant.created",
            tenant_id=tenant.id,
            target_id=str(tenant.id),
            target_type="tenant",
            metadata={"name": tenant.name},
        )
        self._cache_tenant(tenant)
        self._publish_event(
            "tenant.created",
            {
                "tenant_id": str(tenant.id),
                "name": tenant.name,
            },
        )
        ADMIN_ACTION_COUNTER.labels("tenant.created", "success").inc()
        return tenant

    def list_tenants(self) -> list[models.Tenant]:
        return list(
            self._session.exec(select(models.Tenant).order_by(models.Tenant.created_at))
        )

    def update_tenant(
        self,
        tenant_id: UUID,
        request: schemas.TenantUpdateRequest,
        *,
        actor: str,
    ) -> models.Tenant:
        tenant = self._session.get(models.Tenant, tenant_id)
        if tenant is None:
            raise LookupError("tenant_not_found")

        if request.name:
            tenant.name = request.name
        if request.timezone:
            tenant.timezone = request.timezone
        if request.metadata is not None:
            tenant.metadata_json = request.metadata
        if tenant.embed_config:
            if request.embed_theme is not None:
                tenant.embed_config.theme = request.embed_theme
            if request.widget_options is not None:
                tenant.embed_config.widget_options = request.widget_options
        self._session.add(tenant)
        self._session.flush()

        self._record_audit(
            actor=actor,
            action="tenant.updated",
            tenant_id=tenant.id,
            target_id=str(tenant.id),
            target_type="tenant",
            metadata=request.model_dump(exclude_unset=True),
        )
        self._cache_tenant(tenant)
        self._publish_event(
            "tenant.updated",
            {
                "tenant_id": str(tenant.id),
                "name": tenant.name,
            },
        )
        ADMIN_ACTION_COUNTER.labels("tenant.updated", "success").inc()
        return tenant

    # Knowledge asset operations ----------------------------------------

    def list_knowledge_assets(
        self,
        *,
        tenant_id: UUID | None = None,
        brand_id: UUID | None = None,
    ) -> list[models.KnowledgeAsset]:
        statement = select(models.KnowledgeAsset).order_by(
            models.KnowledgeAsset.created_at.desc()
        )
        if tenant_id:
            statement = statement.where(models.KnowledgeAsset.tenant_id == tenant_id)
        if brand_id:
            statement = statement.where(models.KnowledgeAsset.brand_id == brand_id)
        return list(self._session.exec(statement))

    def delete_knowledge_asset(self, asset_id: UUID, *, actor: str) -> None:
        asset = self._session.get(models.KnowledgeAsset, asset_id)
        if asset is None:
            raise LookupError("asset_not_found")
        self._session.delete(asset)
        self._record_audit(
            actor=actor,
            action="knowledge_asset.deleted",
            tenant_id=asset.tenant_id,
            target_id=str(asset.id),
            target_type="knowledge_asset",
            metadata={"knowledge_source_id": str(asset.knowledge_source_id)},
        )

    def update_asset_metadata(
        self,
        asset_id: UUID,
        *,
        tags: list[str] | None = None,
        visibility: models.KnowledgeAssetVisibility | None = None,
    ) -> models.KnowledgeAsset:
        asset = self._session.get(models.KnowledgeAsset, asset_id)
        if asset is None:
            raise LookupError("asset_not_found")
        if tags is not None:
            asset.tags = tags
        if visibility is not None:
            asset.visibility = visibility
        self._session.add(asset)
        self._session.flush()
        return asset

    def list_ingestion_jobs(
        self,
        *,
        tenant_id: UUID | None = None,
        status: models.IngestionJobStatus | None = None,
    ) -> list[models.IngestionJob]:
        statement = select(models.IngestionJob).order_by(
            models.IngestionJob.created_at.desc()
        )
        if tenant_id:
            statement = statement.where(models.IngestionJob.tenant_id == tenant_id)
        if status:
            statement = statement.where(models.IngestionJob.status == status)
        return list(self._session.exec(statement))

    def mark_ingestion_job_status(
        self,
        job_id: UUID,
        *,
        status: models.IngestionJobStatus,
        reason: str | None,
        actor: str,
    ) -> models.IngestionJob:
        job = self._session.get(models.IngestionJob, job_id)
        if job is None:
            raise LookupError("ingestion_job_not_found")
        job.status = status
        now = datetime.now(tz=UTC)
        if status is models.IngestionJobStatus.CANCELLED:
            job.cancelled_at = now
        elif status is models.IngestionJobStatus.PENDING:
            job.started_at = None
            job.completed_at = None
            job.cancelled_at = None
            job.failure_reason = None
            job.logs = []
        job.failure_reason = reason
        self._session.add(job)
        self._session.flush()
        self._record_audit(
            actor=actor,
            action="ingestion.status",
            tenant_id=job.tenant_id,
            target_id=str(job.id),
            target_type="ingestion_job",
            metadata={"status": job.status.value, "reason": reason},
        )
        self._update_ingestion_gauge(job.tenant_id)
        return job

    # Policy + retrieval operations -------------------------------------

    def list_policy_versions(self, tenant_id: UUID) -> list[models.PolicyVersion]:
        statement = (
            select(models.PolicyVersion)
            .where(models.PolicyVersion.tenant_id == tenant_id)
            .order_by(models.PolicyVersion.version.desc())
        )
        return list(self._session.exec(statement))

    def create_policy_draft(
        self,
        tenant_id: UUID,
        *,
        summary: str | None,
        policy_json: dict[str, Any],
        actor: str,
    ) -> models.PolicyVersion:
        current_version = self._session.exec(
            select(models.PolicyVersion.version)
            .where(models.PolicyVersion.tenant_id == tenant_id)
            .order_by(models.PolicyVersion.version.desc())
        ).first()
        next_version = (current_version or 0) + 1
        policy = models.PolicyVersion(
            tenant_id=tenant_id,
            version=next_version,
            status=models.PolicyStatus.DRAFT,
            created_by=actor,
            summary=summary,
            policy_json=policy_json,
        )
        self._session.add(policy)
        self._session.flush()
        self._record_audit(
            actor=actor,
            action="policy.draft_created",
            tenant_id=tenant_id,
            target_id=str(policy.id),
            target_type="policy_version",
            metadata={"version": next_version},
        )
        return policy

    def publish_policy(
        self,
        version_id: UUID,
        *,
        actor: str,
        notes: str | None = None,
    ) -> models.PolicyVersion:
        policy = self._session.get(models.PolicyVersion, version_id)
        if policy is None:
            raise LookupError("policy_version_not_found")
        previous = (
            self._session.exec(
                select(models.PolicyVersion)
                .where(
                    models.PolicyVersion.tenant_id == policy.tenant_id,
                    models.PolicyVersion.status == models.PolicyStatus.PUBLISHED,
                    models.PolicyVersion.id != policy.id,
                )
                .order_by(models.PolicyVersion.version.desc())
            ).first()
            if policy.status != models.PolicyStatus.PUBLISHED
            else None
        )
        policy.status = models.PolicyStatus.PUBLISHED
        policy.published_at = datetime.now(tz=UTC)
        self._session.add(policy)
        self._session.flush()
        diff_payload = self._compute_policy_diff(
            previous.policy_json if previous else None, policy.policy_json
        )
        snapshot = models.PolicySnapshot(
            policy_version_id=policy.id,
            previous_version=previous.version if previous else None,
            diff_json=diff_payload,
            created_by=actor,
            notes=notes,
        )
        self._session.add(snapshot)
        self._session.flush()
        self._record_audit(
            actor=actor,
            action="policy.published",
            tenant_id=policy.tenant_id,
            target_id=str(policy.id),
            target_type="policy_version",
            metadata={"version": policy.version},
        )
        return policy

    def rollback_policy(
        self,
        tenant_id: UUID,
        *,
        target_version: int,
        actor: str,
        notes: str | None = None,
    ) -> models.PolicyVersion:
        target = self._session.exec(
            select(models.PolicyVersion).where(
                models.PolicyVersion.tenant_id == tenant_id,
                models.PolicyVersion.version == target_version,
            )
        ).first()
        if target is None:
            raise LookupError("policy_version_not_found")
        draft = self.create_policy_draft(
            tenant_id,
            summary=f"Rollback to v{target_version}",
            policy_json=target.policy_json,
            actor=actor,
        )
        self.publish_policy(draft.id, actor=actor, notes=notes)
        return draft

    def list_policy_snapshots(self, tenant_id: UUID) -> list[models.PolicySnapshot]:
        statement = (
            select(models.PolicySnapshot)
            .join(
                models.PolicyVersion,
                models.PolicySnapshot.policy_version_id == models.PolicyVersion.id,
            )
            .where(models.PolicyVersion.tenant_id == tenant_id)
            .order_by(models.PolicySnapshot.created_at.desc())
        )
        return list(self._session.exec(statement))

    def get_retrieval_config(self, tenant_id: UUID) -> models.RetrievalConfig:
        config = self._session.exec(
            select(models.RetrievalConfig).where(
                models.RetrievalConfig.tenant_id == tenant_id
            )
        ).first()
        if config:
            return config
        config = models.RetrievalConfig(tenant_id=tenant_id)
        self._session.add(config)
        self._session.flush()
        return config

    def update_retrieval_config(
        self,
        tenant_id: UUID,
        *,
        updates: dict[str, Any],
        actor: str,
    ) -> models.RetrievalConfig:
        config = self.get_retrieval_config(tenant_id)
        for field, value in updates.items():
            if value is None:
                continue
            if hasattr(config, field):
                setattr(config, field, value)
        self._session.add(config)
        self._session.flush()
        self._record_audit(
            actor=actor,
            action="retrieval.config_updated",
            tenant_id=tenant_id,
            target_id=str(config.id),
            target_type="retrieval_config",
            metadata=updates,
        )
        return config

    # Channel operations -------------------------------------------------

    def provision_channel(
        self,
        request: schemas.ChannelCreateRequest,
        *,
        actor: str,
    ) -> tuple[models.ChannelConfig, str]:
        tenant = self._session.get(models.Tenant, request.tenant_id)
        if tenant is None:
            raise LookupError("tenant_not_found")

        brand = self._get_or_create_brand(tenant.id, request.brand_name)
        channel = models.ChannelConfig(
            brand_id=brand.id,
            channel_type=request.channel_type,
            display_name=request.display_name,
            credentials=request.credentials,
            is_active=True,
        )
        self._session.add(channel)
        self._session.flush()

        hmac_secret = secrets.token_urlsafe(32)
        self._persist_channel_secret(
            channel_id=channel.id,
            label="webhook_hmac",
            purpose=models.ChannelSecretPurpose.HMAC,
            secret_value=hmac_secret,
        )

        for label, value in (request.secret_credentials or {}).items():
            self._persist_channel_secret(
                channel_id=channel.id,
                label=label,
                purpose=models.ChannelSecretPurpose.API,
                secret_value=value,
            )

        self._record_audit(
            actor=actor,
            action="channel.created",
            tenant_id=tenant.id,
            target_id=str(channel.id),
            target_type="channel",
            metadata={
                "brand_id": str(brand.id),
                "channel_type": channel.channel_type.value,
                "display_name": channel.display_name,
            },
        )
        self._cache_channel(channel, tenant_id=tenant.id)
        self._publish_event(
            "channel.created",
            {
                "tenant_id": str(tenant.id),
                "channel_id": str(channel.id),
                "channel_type": channel.channel_type.value,
            },
        )
        ADMIN_ACTION_COUNTER.labels("channel.created", "success").inc()
        return channel, hmac_secret

    # Token/embed helpers -----------------------------------------------

    def generate_embed_snippet(
        self,
        tenant_id: UUID,
        *,
        base_url: str,
    ) -> str:
        tenant = self._session.get(models.Tenant, tenant_id)
        if tenant is None or not tenant.embed_config:
            raise LookupError("tenant_not_found")

        nonce = secrets.token_hex(8)
        signature = hashlib.sha256(
            f"{tenant.embed_config.handshake_salt}:{nonce}".encode("utf-8")
        ).hexdigest()
        script_src = f"{base_url.rstrip('/')}/embed.js"
        return (
            f'<script async src="{script_src}" '
            f'data-tenant-id="{tenant_id}" data-nonce="{nonce}" data-signature="{signature}"></script>'
        )

    def list_audit_logs(
        self, *, limit: int = 50, tenant_id: UUID | None = None
    ) -> list[models.AuditLogEntry]:
        statement = (
            select(models.AuditLogEntry)
            .order_by(models.AuditLogEntry.created_at.desc())
            .limit(limit)
        )
        if tenant_id:
            statement = statement.where(models.AuditLogEntry.tenant_id == tenant_id)
        return list(self._session.exec(statement))

    # Internal helpers --------------------------------------------------

    def _persist_channel_secret(
        self,
        *,
        channel_id: UUID,
        label: str,
        purpose: models.ChannelSecretPurpose,
        secret_value: str,
    ) -> None:
        payload = {
            "channel_id": str(channel_id),
            "label": label,
            "purpose": purpose.value,
            "secret": secret_value,
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
        key = f"secrets/{channel_id}/{uuid4()}.json"
        reference = self._storage.store_secret_blob(
            key=key,
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )
        secret = models.ChannelSecret(
            channel_id=channel_id,
            label=label,
            purpose=purpose,
            secret_hash=_hash_secret(secret_value),
            secret_reference=reference,
            rotated_at=datetime.now(tz=UTC),
        )
        self._session.add(secret)

    def _get_or_create_brand(self, tenant_id: UUID, brand_name: str) -> models.Brand:
        slug = _slugify(brand_name)
        statement = select(models.Brand).where(
            models.Brand.tenant_id == tenant_id,
            models.Brand.slug == slug,
        )
        brand = self._session.exec(statement).first()
        if brand:
            return brand

        brand = models.Brand(
            tenant_id=tenant_id,
            name=brand_name,
            slug=slug,
            language="en",
        )
        self._session.add(brand)
        self._session.flush()
        return brand

    def _cache_tenant(self, tenant: models.Tenant) -> None:
        if not self._redis:
            return
        payload = {
            "id": str(tenant.id),
            "name": tenant.name,
            "timezone": tenant.timezone,
            "updated_at": tenant.updated_at.isoformat(),
        }
        self._redis.setex(
            f"admin:tenant:{tenant.id}",
            TENANT_CACHE_TTL_SECONDS,
            json.dumps(payload),
        )

    def _cache_channel(self, channel: models.ChannelConfig, *, tenant_id: UUID) -> None:
        if not self._redis:
            return
        payload = {
            "id": str(channel.id),
            "tenant_id": str(tenant_id),
            "channel_type": channel.channel_type.value,
            "display_name": channel.display_name,
        }
        self._redis.setex(
            f"admin:channel:{channel.id}",
            CHANNEL_CACHE_TTL_SECONDS,
            json.dumps(payload),
        )

    def _publish_event(self, action: str, payload: dict[str, str]) -> None:
        if not self._redis:
            return
        event = {"action": action, "timestamp": datetime.now(tz=UTC).isoformat()}
        event.update({key: str(value) for key, value in payload.items()})
        try:
            self._redis.xadd("admin.events", event, maxlen=1000, approximate=True)
        except Exception:  # pragma: no cover - optional capability
            logger.warning("failed to publish admin event", action=action)

    def _record_audit(
        self,
        *,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        metadata: dict[str, Any] | None,
        tenant_id: UUID | None,
    ) -> None:
        entry = models.AuditLogEntry(
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata,
        )
        self._session.add(entry)

    def _update_ingestion_gauge(self, tenant_id: UUID) -> None:
        if not self._redis:
            return
        running_jobs = list(
            self._session.exec(
                select(models.IngestionJob).where(
                    models.IngestionJob.tenant_id == tenant_id,
                    models.IngestionJob.status == models.IngestionJobStatus.RUNNING,
                )
            )
        )
        INGESTION_JOBS_GAUGE.labels(str(tenant_id)).set(float(len(running_jobs)))

    @staticmethod
    def _compute_policy_diff(
        previous: dict[str, Any] | None,
        current: dict[str, Any],
    ) -> dict[str, Any]:
        if previous is None:
            return {"previous": None, "current": current}
        return {
            "previous": previous,
            "current": current,
        }


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
    return slug or "default"


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
