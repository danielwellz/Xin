"""Minimal object storage helper built on boto3."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import UUID

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from chatbot.core.config import StorageSettings

logger = logging.getLogger(__name__)


_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(slots=True)
class StorageUploadResult:
    """Details about an uploaded document."""

    uri: str
    key: str
    filename: str


class ObjectStorageClient:
    """Thin wrapper for uploading knowledge documents to S3/MinIO."""

    def __init__(self, settings: StorageSettings) -> None:
        self._settings = settings
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            region_name=settings.region,
        )
        self._ensure_bucket()

    def upload_document(
        self,
        *,
        tenant_id: UUID,
        brand_id: UUID,
        knowledge_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> StorageUploadResult:
        safe_name = self._sanitize_filename(filename)
        key = f"knowledge/{tenant_id}/{brand_id}/{knowledge_id}/{safe_name}"
        try:
            self._client.put_object(
                Bucket=self._settings.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError):
            logger.exception("failed to upload knowledge document to object storage")
            raise

        uri = f"s3://{self._settings.bucket}/{key}"
        return StorageUploadResult(uri=uri, key=key, filename=safe_name)

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._settings.bucket)
            return
        except ClientError as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if error_code not in {"404", "NoSuchBucket"}:
                logger.warning(
                    "unable to verify storage bucket; assuming it exists",
                    extra={"bucket": self._settings.bucket, "error": error_code},
                )
                return

        try:
            params: dict[str, object] = {"Bucket": self._settings.bucket}
            if self._settings.region and self._settings.region != "us-east-1":
                params["CreateBucketConfiguration"] = {
                    "LocationConstraint": self._settings.region,
                }
            self._client.create_bucket(**params)
            logger.info(
                "created object storage bucket",
                extra={"bucket": self._settings.bucket},
            )
        except (BotoCoreError, ClientError):
            logger.exception(
                "failed to create object storage bucket",
                extra={"bucket": self._settings.bucket},
            )
            raise

    @staticmethod
    def _sanitize_filename(filename: str | None) -> str:
        candidate = filename or "upload"
        cleaned = _FILENAME_PATTERN.sub("_", candidate).strip("._")
        return cleaned or "upload"
