"""Administrative diagnostics endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from chatbot.admin import schemas
from chatbot.adapters.orchestrator import dependencies
from chatbot.adapters.orchestrator.routers.admin import require_scope
from chatbot.adapters.orchestrator.services import ContextService
from chatbot.policy.engine import PolicyEngine

router = APIRouter(prefix="/admin/diagnostics", tags=["admin-diagnostics"])

ContextDep = Annotated[ContextService, Depends(dependencies.get_context_service)]
PolicyDep = Annotated[PolicyEngine, Depends(dependencies.get_policy_engine)]


@router.post(
    "/retrieval",
    response_model=schemas.RetrievalDiagnosticsResponse,
)
def diagnostics_retrieval(
    request: schemas.RetrievalDiagnosticsRequest,
    context_service: ContextDep,
    policy_engine: PolicyDep,
    claims=Depends(require_scope("platform_admin", "tenant_operator")),
) -> schemas.RetrievalDiagnosticsResponse:
    tenant_id = request.tenant_id
    if (
        claims.has_scope("tenant_operator")
        and claims.tenant_id
        and claims.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )

    channel_id = request.channel_id or UUID(int=0)
    decision = policy_engine.evaluate(
        tenant_id=request.tenant_id,
        brand_id=request.brand_id,
        channel_id=channel_id,
        message=request.message,
    )
    top_k = request.max_documents or decision.top_k
    context = context_service.retrieve(
        tenant_id=request.tenant_id,
        brand_id=request.brand_id,
        message=request.message,
        top_k=top_k,
        min_score=decision.min_score,
        filters=decision.filters,
    )
    docs = []
    for document in context:
        docs.append(
            {
                "id": document.id,
                "text": document.text,
                "metadata": document.metadata,
            }
        )
    applied_config = schemas.RetrievalConfigResponse(
        tenant_id=request.tenant_id,
        hybrid_weight=decision.hybrid_weight,
        min_score=decision.min_score,
        max_documents=decision.top_k,
        context_budget_tokens=decision.context_budget_tokens,
        filters=decision.filters,
        fallback_llm=decision.fallback_llm,
        updated_at=datetime.now(tz=UTC),
    )
    return schemas.RetrievalDiagnosticsResponse(
        query=request.message,
        documents=docs,
        applied_config=applied_config,
    )
