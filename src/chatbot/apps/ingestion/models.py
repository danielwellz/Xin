"""Data models for knowledge ingestion jobs and pipeline artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


class IngestionStatus(str, Enum):
    """Lifecycle statuses for a knowledge ingestion job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeIngestJob(BaseModel):
    """Payload submitted to the ingestion worker."""

    job_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    brand_id: str = Field(..., min_length=1)
    source_uri: str = Field(..., min_length=1, alias="sourceUri")
    content_type: str = Field("text/markdown", alias="contentType")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("source_uri")
    @classmethod
    def _validate_source_uri(cls, value: str) -> str:
        if "://" not in value:
            msg = "source_uri must include a scheme (e.g. s3://bucket/key)"
            raise ValueError(msg)
        return value

    @property
    def namespace(self) -> str:
        """Return the Qdrant namespace for the tenant/brand pair."""

        return f"{self.tenant_id}:{self.brand_id}"


@dataclass(slots=True, frozen=True)
class FetchedDocument:
    """Raw document fetched from object storage."""

    document_id: str
    raw_bytes: bytes
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class NormalizedDocument:
    """Normalized UTF-8 document ready for chunking."""

    document_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ChunkEmbedding:
    """Chunk content with its embedding for vector store persistence."""

    chunk_id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
