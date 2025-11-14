"""Custom exception types for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class IngestionError(Exception):
    """Base exception providing retry metadata."""

    message: str
    retryable: bool = True

    def __str__(self) -> str:  # pragma: no cover - dataclass convenience
        return self.message

    def as_dict(self) -> dict[str, str]:
        return {"message": self.message, "retryable": str(self.retryable)}


class FetchError(IngestionError):
    """Raised when document fetching fails."""


class NormalizationError(IngestionError):
    """Raised when document normalization fails."""


class EmbeddingError(IngestionError):
    """Raised when embedding generation fails."""


class PersistenceError(IngestionError):
    """Raised when vector persistence fails."""
