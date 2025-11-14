"""Admin router implementing tenant onboarding APIs."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chatbot.admin import schemas
from chatbot.admin.auth import TokenClaims, TokenValidationError
from chatbot.admin.service import AdminService
from chatbot.apps.orchestrator import dependencies
from chatbot.core.db import models

router = APIRouter(prefix="/admin", tags=["admin"])

security = HTTPBearer(auto_error=False)
CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(security)]


def _get_current_claims(
    credentials: CredentialsDep,
    jwt_service: dependencies.JWTServiceDep,
) -> TokenClaims:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing credentials"
        )
    try:
        return jwt_service.validate_token(credentials.credentials)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        ) from exc


def require_scope(*scopes: str):
    def _checker(claims: TokenClaims = Depends(_get_current_claims)) -> TokenClaims:
        if any(claims.has_scope(scope) for scope in scopes):
            return claims
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_scope",
        )

    return _checker


AdminServiceDep = Annotated[AdminService, Depends(dependencies.get_admin_service)]


@router.post(
    "/tenants",
    response_model=schemas.TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    request: schemas.TenantCreateRequest,
    service: AdminServiceDep,
    claims: TokenClaims = Depends(require_scope("platform_admin")),
) -> schemas.TenantResponse:
    try:
        tenant = service.create_tenant(request, actor=claims.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="tenant_exists"
        )
    return _to_tenant_response(tenant)


@router.get("/tenants", response_model=list[schemas.TenantResponse])
def list_tenants(
    response: Response,
    service: AdminServiceDep,
    claims: TokenClaims = Depends(require_scope("platform_admin")),
) -> list[schemas.TenantResponse]:
    tenants = service.list_tenants()
    response.headers["ETag"] = _compute_etag(
        [f"{t.id}:{int(t.updated_at.timestamp())}" for t in tenants]
    )
    return [_to_tenant_response(tenant) for tenant in tenants]


@router.patch("/tenants/{tenant_id}", response_model=schemas.TenantResponse)
def update_tenant(
    tenant_id: UUID,
    request: schemas.TenantUpdateRequest,
    service: AdminServiceDep,
    claims: TokenClaims = Depends(require_scope("platform_admin")),
) -> schemas.TenantResponse:
    try:
        tenant = service.update_tenant(tenant_id, request, actor=claims.sub)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found"
        )
    return _to_tenant_response(tenant)


@router.post(
    "/channels",
    response_model=schemas.ChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
def provision_channel(
    request: schemas.ChannelCreateRequest,
    service: AdminServiceDep,
    claims: TokenClaims = Depends(require_scope("platform_admin", "tenant_operator")),
) -> schemas.ChannelResponse:
    if (
        claims.has_scope("tenant_operator")
        and claims.tenant_id
        and claims.tenant_id != request.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )
    try:
        channel, secret = service.provision_channel(request, actor=claims.sub)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found"
        )
    return _to_channel_response(channel, secret)


@router.post(
    "/tokens",
    response_model=schemas.TokenIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_token(
    request: schemas.TokenIssueRequest,
    jwt_service: dependencies.JWTServiceDep,
    claims: TokenClaims = Depends(require_scope("platform_admin")),
) -> schemas.TokenIssueResponse:
    ttl = request.ttl_seconds or jwt_service.ttl_seconds  # type: ignore[attr-defined]
    token = jwt_service.issue_token(
        subject=request.subject,
        roles=request.roles,
        tenant_id=request.tenant_id,
        ttl_override_seconds=ttl,
    )
    token_claims = jwt_service.validate_token(token)
    expires_at = datetime.fromtimestamp(token_claims.exp, tz=UTC)
    return schemas.TokenIssueResponse(token=token, expires_at=expires_at)


@router.get("/embed_snippet/{tenant_id}", response_model=schemas.EmbedSnippetResponse)
def get_embed_snippet(
    tenant_id: UUID,
    request: Request,
    service: AdminServiceDep,
    claims: TokenClaims = Depends(require_scope("platform_admin", "tenant_operator")),
) -> schemas.EmbedSnippetResponse:
    if (
        claims.has_scope("tenant_operator")
        and claims.tenant_id
        and claims.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch"
        )
    base_url = request.query_params.get("base_url") or str(request.base_url).rstrip("/")
    try:
        snippet = service.generate_embed_snippet(tenant_id, base_url=base_url)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found"
        )
    return schemas.EmbedSnippetResponse(tenant_id=tenant_id, snippet=snippet)


@router.get("/audit", response_model=list[schemas.AuditLogEntryResponse])
def list_audit_logs(
    service: AdminServiceDep,
    claims: TokenClaims = Depends(require_scope("platform_admin")),
    limit: int = 50,
    tenant_id: UUID | None = None,
) -> list[schemas.AuditLogEntryResponse]:
    limit = min(max(limit, 1), 200)
    entries = service.list_audit_logs(limit=limit, tenant_id=tenant_id)
    return [
        schemas.AuditLogEntryResponse.model_validate(entry, from_attributes=True)
        for entry in entries
    ]


def _to_tenant_response(tenant: models.Tenant) -> schemas.TenantResponse:  # type: ignore[name-defined]
    embed_config = None
    if tenant.embed_config:
        embed_config = schemas.EmbedConfigResponse(
            tenant_id=tenant.id,
            handshake_salt=tenant.embed_config.handshake_salt,
            token_ttl_seconds=tenant.embed_config.token_ttl_seconds,
            theme=tenant.embed_config.theme,
            widget_options=tenant.embed_config.widget_options,
        )
    return schemas.TenantResponse(
        id=tenant.id,
        name=tenant.name,
        timezone=tenant.timezone,
        metadata=tenant.metadata_json,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        embed_config=embed_config,
    )


def _to_channel_response(
    channel: models.ChannelConfig,  # type: ignore[name-defined]
    secret: str,
) -> schemas.ChannelResponse:
    return schemas.ChannelResponse(
        id=channel.id,
        brand_id=channel.brand_id,
        channel_type=channel.channel_type,
        display_name=channel.display_name,
        is_active=channel.is_active,
        credentials=channel.credentials,
        hmac_secret=secret,
    )


def _compute_etag(values: list[str]) -> str:
    joined = "|".join(values)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
