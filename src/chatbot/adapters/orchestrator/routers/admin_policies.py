"""Admin policy and retrieval configuration endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from chatbot.admin import schemas
from chatbot.admin.service import AdminService
from chatbot.adapters.orchestrator import dependencies
from chatbot.adapters.orchestrator.routers.admin import require_scope
from chatbot.core.db import models

router = APIRouter(prefix="/admin", tags=["admin-policies"])

AdminServiceDep = Annotated[AdminService, Depends(dependencies.get_admin_service)]


def _policy_to_response(policy: models.PolicyVersion) -> schemas.PolicyVersionResponse:
    return schemas.PolicyVersionResponse(
        id=policy.id,
        version=policy.version,
        status=policy.status,
        summary=policy.summary,
        created_at=policy.created_at,
        published_at=policy.published_at,
    )


@router.get(
    "/policies/{tenant_id}",
    response_model=list[schemas.PolicyVersionResponse],
)
def list_policies(
    tenant_id: UUID,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> list[schemas.PolicyVersionResponse]:
    if (
        claims.has_scope("tenant_operator")
        and claims.tenant_id
        and claims.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )
    policies = service.list_policy_versions(tenant_id)
    return [_policy_to_response(policy) for policy in policies]


@router.post(
    "/policies/{tenant_id}/draft",
    response_model=schemas.PolicyVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_draft(
    tenant_id: UUID,
    request: schemas.PolicyDraftRequest,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.PolicyVersionResponse:
    policy = service.create_policy_draft(
        tenant_id,
        summary=request.summary,
        policy_json=request.policy_json,
        actor=claims.sub,
    )
    return _policy_to_response(policy)


@router.post(
    "/policies/{tenant_id}/publish",
    response_model=schemas.PolicyVersionResponse,
)
def publish_policy(
    tenant_id: UUID,
    request: schemas.PolicyPublishRequest,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.PolicyVersionResponse:
    policy = service.publish_policy(
        request.version_id, actor=claims.sub, notes=request.notes
    )
    if policy.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_mismatch"
        )
    return _policy_to_response(policy)


@router.post(
    "/policies/{tenant_id}/rollback",
    response_model=schemas.PolicyVersionResponse,
)
def rollback_policy(
    tenant_id: UUID,
    request: schemas.PolicyRollbackRequest,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.PolicyVersionResponse:
    policy = service.rollback_policy(
        tenant_id,
        target_version=request.target_version,
        actor=claims.sub,
        notes=request.notes,
    )
    return _policy_to_response(policy)


@router.get(
    "/policies/{tenant_id}/diff/{version}",
    response_model=schemas.PolicyDiffResponse,
)
def get_policy_diff(
    tenant_id: UUID,
    version: int,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> schemas.PolicyDiffResponse:
    snapshots = service.list_policy_snapshots(tenant_id)
    snapshot = next(
        (
            item
            for item in snapshots
            if item.policy_version and item.policy_version.version == version
        ),
        None,
    )
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="diff_not_found"
        )
    policy_version = snapshot.policy_version
    if policy_version is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="diff_corrupt"
        )
    return schemas.PolicyDiffResponse(
        version=version,
        previous_version=snapshot.previous_version,
        diff_json=snapshot.diff_json,
        created_at=snapshot.created_at,
        created_by=snapshot.created_by,
        notes=snapshot.notes,
    )


@router.get(
    "/policies/{tenant_id}/retrieval_config",
    response_model=schemas.RetrievalConfigResponse,
)
def get_retrieval_config(
    tenant_id: UUID,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> schemas.RetrievalConfigResponse:
    config = service.get_retrieval_config(tenant_id)
    return schemas.RetrievalConfigResponse(
        tenant_id=tenant_id,
        hybrid_weight=config.hybrid_weight,
        min_score=config.min_score,
        max_documents=config.max_documents,
        context_budget_tokens=config.context_budget_tokens,
        filters=config.filters,
        fallback_llm=config.fallback_llm,
        updated_at=config.updated_at,
    )


@router.put(
    "/policies/{tenant_id}/retrieval_config",
    response_model=schemas.RetrievalConfigResponse,
)
def update_retrieval_config(
    tenant_id: UUID,
    request: schemas.RetrievalConfigRequest,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.RetrievalConfigResponse:
    config = service.update_retrieval_config(
        tenant_id,
        updates=request.model_dump(exclude_none=True),
        actor=claims.sub,
    )
    return schemas.RetrievalConfigResponse(
        tenant_id=tenant_id,
        hybrid_weight=config.hybrid_weight,
        min_score=config.min_score,
        max_documents=config.max_documents,
        context_budget_tokens=config.context_budget_tokens,
        filters=config.filters,
        fallback_llm=config.fallback_llm,
        updated_at=config.updated_at,
    )
