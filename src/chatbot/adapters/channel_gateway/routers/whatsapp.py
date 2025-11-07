"""WhatsApp webhook router."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from httpx import HTTPError

from chatbot.core.domain import ChannelType

from ..adapters.orchestrator import OrchestratorClient
from ..dependencies import SettingsDep, get_orchestrator_client
from ..models import ProviderInboundEnvelope, SignatureContext
from ..utils.exceptions import SignatureVerificationError
from ..utils.security import validate_hmac_signature

OrchestratorDep = Annotated[OrchestratorClient, Depends(get_orchestrator_client)]

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def whatsapp_webhook(
    request: Request,
    orchestrator: OrchestratorDep,
    settings: SettingsDep,
) -> dict[str, str]:
    raw_body = await request.body()
    signature = request.headers.get("X-WHATSAPP-SIGNATURE", "")

    try:
        validate_hmac_signature(
            SignatureContext(signature=signature, secret=settings.whatsapp_secret, payload=raw_body)
        )
    except SignatureVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid JSON payload"
        ) from exc

    envelope = _parse_payload(payload)
    message = envelope.to_inbound_message(channel_type=ChannelType.WHATSAPP)

    try:
        await orchestrator.forward_inbound(message)
    except HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="orchestrator unavailable"
        ) from exc

    return {"status": "accepted"}


def _parse_payload(payload: dict[str, object]) -> ProviderInboundEnvelope:
    try:
        tenant_id = UUID(str(payload["tenant_id"]))
        brand_id = UUID(str(payload["brand_id"]))
        channel_id = UUID(str(payload["channel_id"]))
        sender_id = str(payload["sender_id"])
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"missing field {exc.args[0]}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    occurred_at_str = payload.get("timestamp")
    if isinstance(occurred_at_str, str):
        occurred_at = datetime.fromisoformat(occurred_at_str)
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
    else:
        occurred_at = datetime.now(tz=UTC)

    conversation_id = payload.get("conversation_id")
    parsed_conversation = None
    if isinstance(conversation_id, str):
        try:
            parsed_conversation = UUID(conversation_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid conversation_id",
            ) from exc

    locale = str(payload["locale"]) if "locale" in payload else None
    attachments = payload.get("attachments")
    if not isinstance(attachments, list):
        attachments = []

    content = str(payload.get("message") or payload.get("content") or "").strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="missing message content"
        )

    return ProviderInboundEnvelope(
        event_id=str(payload.get("event_id")),
        tenant_id=tenant_id,
        brand_id=brand_id,
        channel_id=channel_id,
        sender_id=sender_id,
        conversation_id=parsed_conversation,
        content=content,
        occurred_at=occurred_at,
        locale=locale,
        metadata=payload.get("metadata") or {},
        attachments=attachments,
    )
