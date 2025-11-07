"""Document normalization strategies."""

from __future__ import annotations

from collections.abc import Callable

from .errors import NormalizationError
from .models import FetchedDocument, KnowledgeIngestJob, NormalizedDocument


class MarkdownNormalizer:
    """Decode UTF-8 markdown documents and merge base metadata."""

    def __init__(self, *, transform: Callable[[str], str] | None = None) -> None:
        self._transform = transform or (lambda text: text)

    def normalize(self, job: KnowledgeIngestJob, document: FetchedDocument) -> NormalizedDocument:
        try:
            text = document.raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NormalizationError("document is not valid UTF-8", retryable=False) from exc

        text = self._transform(text).strip()
        if not text:
            raise NormalizationError("document is empty after normalization", retryable=False)

        metadata = {
            "tenant_id": job.tenant_id,
            "brand_id": job.brand_id,
            "source_uri": job.source_uri,
            **{key: str(value) for key, value in document.metadata.items()},
        }
        return NormalizedDocument(document_id=document.document_id, text=text, metadata=metadata)
