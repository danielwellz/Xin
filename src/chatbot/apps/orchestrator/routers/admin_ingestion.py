"""Admin ingestion and knowledge asset management."""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from chatbot.admin import schemas
from chatbot.admin.service import AdminService
from chatbot.apps.orchestrator import dependencies
from chatbot.apps.orchestrator.routers.admin import require_scope
from chatbot.apps.orchestrator.services import (
    KnowledgeRegistrationResult,
    KnowledgeService,
)
from chatbot.apps.orchestrator.tasks import IngestionJobPublisher
from chatbot.core.db import models

router = APIRouter(prefix="/admin", tags=["admin-ingestion"])

AdminServiceDep = Annotated[AdminService, Depends(dependencies.get_admin_service)]
KnowledgeServiceDep = Annotated[
    KnowledgeService, Depends(dependencies.get_knowledge_service)
]
PublisherDep = Annotated[
    IngestionJobPublisher, Depends(dependencies.get_ingestion_job_publisher)
]


def _asset_to_response(asset: models.KnowledgeAsset) -> schemas.KnowledgeAssetResponse:
    return schemas.KnowledgeAssetResponse(
        id=asset.id,
        tenant_id=asset.tenant_id,
        brand_id=asset.brand_id,
        knowledge_source_id=asset.knowledge_source_id,
        title=asset.title,
        tags=asset.tags,
        visibility=asset.visibility,
        status=asset.status,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _job_to_response(job: models.IngestionJob) -> schemas.IngestionJobResponse:
    return schemas.IngestionJobResponse(
        id=job.id,
        knowledge_source_id=job.knowledge_source_id,
        tenant_id=job.tenant_id,
        brand_id=job.brand_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        cancelled_at=job.cancelled_at,
        total_chunks=job.total_chunks,
        processed_chunks=job.processed_chunks,
        failure_reason=job.failure_reason,
        logs=job.logs,
    )


@router.get(
    "/knowledge_assets",
    response_model=list[schemas.KnowledgeAssetResponse],
)
def list_assets(
    tenant_id: UUID | None = None,
    brand_id: UUID | None = None,
    *,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> list[schemas.KnowledgeAssetResponse]:
    if (
        claims.has_scope("tenant_operator")
        and claims.tenant_id
        and tenant_id
        and claims.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )
    assets = service.list_knowledge_assets(tenant_id=tenant_id, brand_id=brand_id)
    return [_asset_to_response(asset) for asset in assets]


@router.delete("/knowledge_assets/{asset_id}")
def delete_asset(
    asset_id: UUID,
    *,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> Response:
    service.delete_knowledge_asset(asset_id, actor=claims.sub)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/knowledge_assets/upload",
    response_model=schemas.KnowledgeAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    tenant_id: Annotated[UUID, Form(...)],
    brand_id: Annotated[UUID, Form(...)],
    file: Annotated[UploadFile, File(...)],
    visibility: Annotated[str | None, Form()] = None,
    tags: Annotated[str | None, Form()] = None,
    *,
    service: AdminServiceDep,
    knowledge_service: KnowledgeServiceDep,
    publisher: PublisherDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> schemas.KnowledgeAssetResponse:
    if (
        claims.has_scope("tenant_operator")
        and claims.tenant_id
        and claims.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="empty upload"
        )

    registration = knowledge_service.register_document(
        brand_id=brand_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "text/plain",
        data=contents,
    )
    if registration.asset_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="asset_not_created",
        )

    parsed_tags = json.loads(tags) if tags else None
    visibility_enum = (
        models.KnowledgeAssetVisibility(visibility)
        if visibility
        else models.KnowledgeAssetVisibility.PRIVATE
    )
    asset = service.update_asset_metadata(
        registration.asset_id,
        tags=parsed_tags,
        visibility=visibility_enum,
    )

    if registration.should_enqueue:
        await publisher.enqueue_job(registration)
        service.mark_ingestion_job_status(
            registration.ingestion_job_id or registration.knowledge.id,
            status=models.IngestionJobStatus.PENDING,
            reason=None,
            actor=claims.sub,
        )

    return _asset_to_response(asset)


@router.get(
    "/ingestion_jobs",
    response_model=list[schemas.IngestionJobResponse],
)
def list_ingestion_jobs(
    tenant_id: UUID | None = None,
    status: models.IngestionJobStatus | None = None,
    *,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> list[schemas.IngestionJobResponse]:
    if (
        claims.has_scope("tenant_operator")
        and claims.tenant_id
        and tenant_id
        and claims.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )
    jobs = service.list_ingestion_jobs(tenant_id=tenant_id, status=status)
    return [_job_to_response(job) for job in jobs]


@router.post(
    "/ingestion_jobs/{job_id}/retry",
    response_model=schemas.IngestionJobResponse,
)
async def retry_ingestion_job(
    job_id: UUID,
    request: schemas.IngestionJobActionRequest,
    *,
    service: AdminServiceDep,
    publisher: PublisherDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.IngestionJobResponse:
    job = service.mark_ingestion_job_status(
        job_id,
        status=models.IngestionJobStatus.PENDING,
        reason=request.reason,
        actor=claims.sub,
    )
    knowledge_source = job.knowledge_source
    if knowledge_source is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="knowledge_source_missing"
        )
    asset = knowledge_source.asset
    registration = KnowledgeRegistrationResult(
        knowledge=knowledge_source,
        tenant_id=job.tenant_id,
        brand_id=job.brand_id,
        filename=(knowledge_source.metadata_json or {}).get("filename", "upload"),
        content_type=(knowledge_source.metadata_json or {}).get(
            "content_type", "text/plain"
        ),
        source_uri=knowledge_source.source_uri,
        asset_id=asset.id if asset else None,
        ingestion_job_id=job.id,
    )
    await publisher.enqueue_job(registration)
    return _job_to_response(job)


@router.post(
    "/ingestion_jobs/{job_id}/cancel",
    response_model=schemas.IngestionJobResponse,
)
def cancel_ingestion_job(
    job_id: UUID,
    request: schemas.IngestionJobActionRequest,
    *,
    service: AdminServiceDep,
    claims=Depends(require_scope("platform_admin")),
) -> schemas.IngestionJobResponse:
    job = service.mark_ingestion_job_status(
        job_id,
        status=models.IngestionJobStatus.CANCELLED,
        reason=request.reason,
        actor=claims.sub,
    )
    return _job_to_response(job)
