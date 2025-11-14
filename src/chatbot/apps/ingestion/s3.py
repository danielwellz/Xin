"""Adapters for fetching documents from S3-compatible storage."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlparse

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from chatbot.apps.ingestion.errors import FetchError
from chatbot.apps.ingestion.models import FetchedDocument, KnowledgeIngestJob


@dataclass(slots=True)
class MinioFetcherSettings:
    """Runtime configuration for MinIO fetcher."""

    endpoint_url: str
    access_key: str
    secret_key: str
    region_name: str = "us-east-1"
    max_attempts: int = 3


class MinioDocumentFetcher:
    """Fetch objects from S3-compatible MinIO storage."""

    def __init__(
        self,
        *,
        settings: MinioFetcherSettings,
        session: aioboto3.Session | None = None,
    ) -> None:
        self._settings = settings
        self._session = session or aioboto3.Session()

    async def fetch(self, job: KnowledgeIngestJob) -> list[FetchedDocument]:
        uris = self._extract_object_uris(job)
        documents: list[FetchedDocument] = []

        client_kwargs = {
            "endpoint_url": self._settings.endpoint_url,
            "aws_access_key_id": self._settings.access_key,
            "aws_secret_access_key": self._settings.secret_key,
            "region_name": self._settings.region_name,
        }

        try:
            async with self._session.client("s3", **client_kwargs) as client:
                for uri in uris:
                    bucket, key = _parse_s3_uri(uri)
                    response = await client.get_object(Bucket=bucket, Key=key)
                    body = await response["Body"].read()
                    documents.append(
                        FetchedDocument(
                            document_id=key,
                            raw_bytes=body,
                            metadata={
                                "bucket": bucket,
                                "object_key": key,
                                "content_type": response.get("ContentType")
                                or job.content_type,
                            },
                        )
                    )
        except (ClientError, BotoCoreError) as exc:
            raise FetchError(
                "failed to fetch object from MinIO", retryable=True
            ) from exc
        except asyncio.CancelledError:  # pragma: no cover - propagation
            raise
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise FetchError(
                "unexpected error fetching from MinIO", retryable=True
            ) from exc

        return documents

    def _extract_object_uris(self, job: KnowledgeIngestJob) -> Sequence[str]:
        metadata = job.metadata or {}
        extra_objects = metadata.get("source_objects")
        if isinstance(extra_objects, Sequence) and not isinstance(
            extra_objects, str | bytes
        ):
            return [str(uri) for uri in extra_objects]
        return [job.source_uri]


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme not in {"s3", "minio"}:
        msg = f"unsupported URI scheme for S3 object: {parsed.scheme}"
        raise FetchError(msg, retryable=False)
    if not parsed.netloc or not parsed.path:
        raise FetchError("S3 URI must include bucket and key", retryable=False)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    return bucket, key
