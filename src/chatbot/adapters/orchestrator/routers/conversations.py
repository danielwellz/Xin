"""Conversation history endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import NoResultFound

from chatbot.core.http import ResponseEnvelope

from .. import schemas
from ..dependencies import get_conversation_service
from ..services import ConversationService, convert_message_log

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])

ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]


@router.get(
    "/{conversation_id}",
    response_model=ResponseEnvelope[schemas.ConversationHistoryResponse],
    status_code=status.HTTP_200_OK,
)
def get_conversation_history(
    conversation_id: UUID,
    conversation_service: ConversationServiceDep,
) -> ResponseEnvelope[schemas.ConversationHistoryResponse]:
    """Return the persisted message history for a conversation."""

    try:
        conversation = conversation_service.fetch_conversation(conversation_id)
    except NoResultFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    messages = conversation_service.get_history(conversation_id, limit=0)
    payload = schemas.ConversationHistoryResponse(
        conversation_id=conversation.id,
        channel_id=conversation.channel_config_id,
        status=conversation.status,
        messages=[convert_message_log(message) for message in messages],
    )
    return ResponseEnvelope(data=payload)
