"""Knowledge ingestion endpoints."""

from __future__ import annotations

import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import NoResultFound

from chatbot.core.http import ResponseEnvelope

from .. import schemas
from ..dependencies import get_knowledge_service
from ..services import KnowledgeService

router = APIRouter(prefix="/v1/brands", tags=["knowledge"])

SUPPORTED_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
}


@router.post(
    "/{brand_id}/knowledge",
    response_model=ResponseEnvelope[schemas.KnowledgeUploadResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_knowledge_document(
    brand_id: UUID,
    file: Annotated[UploadFile, File(...)],
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> ResponseEnvelope[schemas.KnowledgeUploadResponse]:
    """Stage an uploaded document for ingestion into the knowledge base."""

    content_type = file.content_type or "application/octet-stream"
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported content type: {content_type}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="empty file upload")

    _ensure_text_extractable(content_type, data)

    try:
        knowledge = knowledge_service.register_document(
            brand_id=brand_id,
            filename=file.filename or "upload",
            content_type=content_type,
            data=data,
            source_uri=file.filename or "upload",
        )
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    response = schemas.KnowledgeUploadResponse(
        knowledge_source_id=knowledge.id,
        filename=file.filename or "upload",
        status=knowledge.status.value,
    )
    return ResponseEnvelope(data=response)


def _ensure_text_extractable(content_type: str, data: bytes) -> None:
    """Validate that the document has extractable text."""

    if content_type == "application/pdf":
        try:
            import textract
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="PDF ingestion requires the 'textract' package",
            ) from exc

        text = textract.process(io.BytesIO(data), extension="pdf").decode(
            "utf-8",
            errors="ignore",
        )  # pragma: no cover - heavy dependency
        if not text.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="unable to extract text from PDF"
            )
        return

    decoded = data.decode("utf-8", errors="ignore")
    if not decoded.strip():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="file does not contain textual content"
        )
