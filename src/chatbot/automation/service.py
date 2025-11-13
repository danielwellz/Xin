"""Administrative helpers for automation rules and jobs."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from prometheus_client import Counter, Gauge
from redis import Redis
from sqlmodel import Session, select

from chatbot.admin import schemas as admin_schemas
from chatbot.automation.connectors import ConnectorContext, build_connector
from chatbot.core.db import models

logger = logging.getLogger(__name__)

AUTOMATION_QUEUE_GAUGE = Gauge(
    "automation_queue_depth",
    "Number of pending automation jobs per tenant.",
    ["tenant_id"],
)

AUTOMATION_FAILURES = Counter(
    "automation_failures_total",
    "Number of automation job failures recorded via admin actions.",
    ["tenant_id"],
)


class AutomationService:
    """Encapsulates automation rule CRUD and job controls."""

    def __init__(self, session: Session, redis_client: Redis | None) -> None:
        self._session = session
        self._redis = redis_client

    def list_rules(
        self, tenant_id: UUID | None = None, brand_id: UUID | None = None
    ) -> list[models.AutomationRule]:
        statement = select(models.AutomationRule).order_by(
            models.AutomationRule.created_at.desc()
        )
        if tenant_id:
            statement = statement.where(models.AutomationRule.tenant_id == tenant_id)
        if brand_id:
            statement = statement.where(models.AutomationRule.brand_id == brand_id)
        return list(self._session.exec(statement))

    def create_rule(
        self,
        request: admin_schemas.AutomationRuleCreateRequest,
        *,
        actor: str,
    ) -> models.AutomationRule:
        brand = self._session.get(models.Brand, request.brand_id)
        if brand is None:
            raise LookupError("brand_not_found")
        rule = models.AutomationRule(
            tenant_id=brand.tenant_id,
            brand_id=brand.id,
            name=request.name,
            trigger_type=request.trigger_type,
            trigger_event=request.trigger_event,
            schedule_expression=request.schedule_expression,
            condition=request.condition,
            action_type=request.action_type,
            action_payload=request.action_payload,
            throttle_seconds=request.throttle_seconds,
            max_retries=request.max_retries,
            is_active=request.is_active,
        )
        self._session.add(rule)
        self._session.flush()
        self._record_audit(
            rule, actor=actor, action="created", metadata={"rule_id": str(rule.id)}
        )
        self._publish_event(
            "automation.rule.created",
            {"rule_id": str(rule.id), "tenant_id": str(rule.tenant_id)},
        )
        return rule

    def update_rule(
        self,
        rule_id: UUID,
        request: admin_schemas.AutomationRuleUpdateRequest,
        *,
        actor: str,
    ) -> models.AutomationRule:
        rule = self._session.get(models.AutomationRule, rule_id)
        if rule is None:
            raise LookupError("automation_rule_not_found")
        update_data = request.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        self._session.add(rule)
        self._session.flush()
        self._record_audit(rule, actor=actor, action="updated", metadata=update_data)
        self._publish_event(
            "automation.rule.updated",
            {"rule_id": str(rule.id), "tenant_id": str(rule.tenant_id)},
        )
        return rule

    def set_rule_active(
        self, rule_id: UUID, *, active: bool, actor: str
    ) -> models.AutomationRule:
        rule = self._session.get(models.AutomationRule, rule_id)
        if rule is None:
            raise LookupError("automation_rule_not_found")
        rule.is_active = active
        rule.paused_at = None if active else datetime.now(tz=UTC)
        self._session.add(rule)
        self._session.flush()
        self._record_audit(
            rule, actor=actor, action="activated" if active else "paused", metadata=None
        )
        self._publish_event(
            "automation.rule.toggled",
            {
                "rule_id": str(rule.id),
                "tenant_id": str(rule.tenant_id),
                "active": str(active),
            },
        )
        return rule

    def test_rule(
        self,
        request: admin_schemas.AutomationTestRequest,
    ) -> dict[str, str]:
        connector = build_connector(request.rule.action_type)
        context = ConnectorContext(
            tenant_id=request.rule.tenant_id,
            brand_id=request.rule.brand_id,
            rule_id=None,
        )
        result = connector.execute(
            request.rule.action_payload,
            dry_run=True,
            context=context,
        )
        return result

    def list_jobs(
        self,
        *,
        tenant_id: UUID | None = None,
        status: models.AutomationJobStatus | None = None,
    ) -> list[models.AutomationJob]:
        statement = select(models.AutomationJob).order_by(
            models.AutomationJob.created_at.desc()
        )
        if tenant_id:
            statement = statement.where(models.AutomationJob.tenant_id == tenant_id)
        if status:
            statement = statement.where(models.AutomationJob.status == status)
        return list(self._session.exec(statement))

    def cancel_job(self, job_id: UUID, *, actor: str) -> models.AutomationJob:
        job = self._session.get(models.AutomationJob, job_id)
        if job is None:
            raise LookupError("automation_job_not_found")
        was_active = job.status in (
            models.AutomationJobStatus.PENDING,
            models.AutomationJobStatus.RUNNING,
        )
        job.status = models.AutomationJobStatus.CANCELLED
        job.completed_at = datetime.now(tz=UTC)
        self._session.add(job)
        self._session.flush()
        if was_active:
            AUTOMATION_QUEUE_GAUGE.labels(str(job.tenant_id)).dec()
        self._record_audit(
            self._resolve_rule(job),
            actor=actor,
            action="job_cancelled",
            metadata={"job_id": str(job.id)},
        )
        return job

    def retry_job(self, job_id: UUID, *, actor: str) -> models.AutomationJob:
        job = self._session.get(models.AutomationJob, job_id)
        if job is None:
            raise LookupError("automation_job_not_found")
        job.status = models.AutomationJobStatus.PENDING
        job.attempts = 0
        job.failure_reason = None
        job.started_at = None
        job.completed_at = None
        job.scheduled_for = datetime.now(tz=UTC)
        self._session.add(job)
        self._session.flush()
        AUTOMATION_QUEUE_GAUGE.labels(str(job.tenant_id)).inc()
        self._record_audit(
            self._resolve_rule(job),
            actor=actor,
            action="job_retry",
            metadata={"job_id": str(job.id)},
        )
        return job

    def record_job_failure(self, job: models.AutomationJob, *, reason: str) -> None:
        AUTOMATION_FAILURES.labels(str(job.tenant_id)).inc()
        self._publish_event(
            "automation.job.failed",
            {"job_id": str(job.id), "tenant_id": str(job.tenant_id), "reason": reason},
        )

    def _record_audit(
        self,
        rule: models.AutomationRule,
        *,
        actor: str,
        action: str,
        metadata: dict[str, object] | None,
    ) -> None:
        audit = models.AutomationAudit(
            tenant_id=rule.tenant_id,
            rule_id=rule.id,
            actor=actor,
            action=action,
            metadata_json=metadata,
        )
        self._session.add(audit)

    def _resolve_rule(self, job: models.AutomationJob) -> models.AutomationRule:
        if job.rule:
            return job.rule
        rule = self._session.get(models.AutomationRule, job.rule_id)
        if rule is None:
            raise LookupError("automation_rule_not_found")
        return rule

    def _publish_event(self, action: str, payload: dict[str, str]) -> None:
        if not self._redis:
            return
        event = {"action": action, "timestamp": datetime.now(tz=UTC).isoformat()}
        event.update(payload)
        try:
            self._redis.xadd("admin.events", event, maxlen=1000, approximate=True)
        except Exception:  # pragma: no cover
            logger.warning(
                "failed to publish automation event", extra={"action": action}
            )
