"""Admin automation endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from chatbot.admin import schemas
from chatbot.apps.orchestrator import dependencies
from chatbot.apps.orchestrator.routers.admin import require_scope
from chatbot.automation.service import AutomationService
from chatbot.core.db import models

router = APIRouter(prefix="/admin/automation", tags=["admin-automation"])

AutomationServiceDep = Annotated[
    AutomationService, Depends(dependencies.get_automation_service)
]


def _rule_response(rule: models.AutomationRule) -> schemas.AutomationRuleResponse:
    return schemas.AutomationRuleResponse(
        id=rule.id,
        tenant_id=rule.tenant_id,
        brand_id=rule.brand_id,
        name=rule.name,
        trigger_type=rule.trigger_type,
        trigger_event=rule.trigger_event,
        schedule_expression=rule.schedule_expression,
        condition=rule.condition,
        action_type=rule.action_type,
        action_payload=rule.action_payload,
        throttle_seconds=rule.throttle_seconds,
        max_retries=rule.max_retries,
        is_active=rule.is_active,
        last_run_at=rule.last_run_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _job_response(job: models.AutomationJob) -> schemas.AutomationJobResponse:
    return schemas.AutomationJobResponse(
        id=job.id,
        rule_id=job.rule_id,
        tenant_id=job.tenant_id,
        brand_id=job.brand_id,
        status=job.status,
        attempts=job.attempts,
        scheduled_for=job.scheduled_for,
        started_at=job.started_at,
        completed_at=job.completed_at,
        payload=job.payload,
        failure_reason=job.failure_reason,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/rules", response_model=list[schemas.AutomationRuleResponse])
def list_rules(
    tenant_id: UUID | None = None,
    brand_id: UUID | None = None,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> list[schemas.AutomationRuleResponse]:
    if (
        claims.has_scope("tenant_operator")
        and tenant_id
        and claims.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )
    rules = service.list_rules(tenant_id=tenant_id, brand_id=brand_id)
    return [_rule_response(rule) for rule in rules]


@router.post(
    "/rules",
    response_model=schemas.AutomationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rule(
    request: schemas.AutomationRuleCreateRequest,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.AutomationRuleResponse:
    rule = service.create_rule(request, actor=claims.sub)
    return _rule_response(rule)


@router.patch(
    "/rules/{rule_id}",
    response_model=schemas.AutomationRuleResponse,
)
def update_rule(
    rule_id: UUID,
    request: schemas.AutomationRuleUpdateRequest,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.AutomationRuleResponse:
    try:
        rule = service.update_rule(rule_id, request, actor=claims.sub)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _rule_response(rule)


@router.post("/rules/{rule_id}/pause", response_model=schemas.AutomationRuleResponse)
def pause_rule(
    rule_id: UUID,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.AutomationRuleResponse:
    try:
        rule = service.set_rule_active(rule_id, active=False, actor=claims.sub)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _rule_response(rule)


@router.post("/rules/{rule_id}/resume", response_model=schemas.AutomationRuleResponse)
def resume_rule(
    rule_id: UUID,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.AutomationRuleResponse:
    try:
        rule = service.set_rule_active(rule_id, active=True, actor=claims.sub)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _rule_response(rule)


@router.post("/test", response_model=dict[str, str])
def test_rule(
    request: schemas.AutomationTestRequest,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> dict[str, str]:
    if (
        claims.has_scope("tenant_operator")
        and claims.tenant_id
        and request.rule.tenant_id != claims.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )
    return service.test_rule(request)


@router.get("/jobs", response_model=list[schemas.AutomationJobResponse])
def list_jobs(
    tenant_id: UUID | None = None,
    status: models.AutomationJobStatus | None = None,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> list[schemas.AutomationJobResponse]:
    if (
        claims.has_scope("tenant_operator")
        and tenant_id
        and claims.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )
    jobs = service.list_jobs(tenant_id=tenant_id, status=status)
    return [_job_response(job) for job in jobs]


@router.post("/jobs/{job_id}/cancel", response_model=schemas.AutomationJobResponse)
def cancel_job(
    job_id: UUID,
    request: schemas.AutomationJobActionRequest,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.AutomationJobResponse:
    try:
        job = service.cancel_job(job_id, actor=claims.sub)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _job_response(job)


@router.post("/jobs/{job_id}/retry", response_model=schemas.AutomationJobResponse)
def retry_job(
    job_id: UUID,
    request: schemas.AutomationJobActionRequest,
    *,
    service: AutomationServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.AutomationJobResponse:
    try:
        job = service.retry_job(job_id, actor=claims.sub)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _job_response(job)
