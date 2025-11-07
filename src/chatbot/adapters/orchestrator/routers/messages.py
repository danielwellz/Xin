"""Inbound message routing."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import NoResultFound

from chatbot.core.http import ResponseEnvelope

from .. import schemas
from ..dependencies import get_orchestrator_service
from ..services import GuardrailViolation, OrchestratorService

router = APIRouter(prefix="/v1/messages", tags=["messages"])

OrchestratorServiceDep = Annotated[OrchestratorService, Depends(get_orchestrator_service)]


@router.post(
    "/inbound",
    response_model=ResponseEnvelope[schemas.InboundMessageResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def handle_inbound_message(
    payload: schemas.InboundMessageRequest,
    orchestrator: OrchestratorServiceDep,
) -> ResponseEnvelope[schemas.InboundMessageResponse]:
    """Process an inbound message payload and emit the orchestrator response."""

    try:
        result = orchestrator.process_inbound(payload)
    except GuardrailViolation as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    response_payload = result.to_response()
    return ResponseEnvelope(data=response_payload, trace_id=result.trace_id)
