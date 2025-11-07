from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

from locust import HttpUser, between, task

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrandProfile:
    """Static metadata describing how a brand interacts with the platform."""

    slug: str
    brand_id: str
    channel_id: str


TENANT_ID = os.getenv("LOCUST_TENANT_ID", "11111111-1111-1111-1111-111111111111")
BRAND_PROFILES = (
    BrandProfile(
        slug="alpha",
        brand_id="22222222-2222-2222-2222-222222222222",
        channel_id="33333333-3333-3333-3333-333333333333",
    ),
    BrandProfile(
        slug="beta",
        brand_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        channel_id="33333333-3333-3333-3333-333333333333",
    ),
)
TARGET_USERS_PER_BRAND = int(os.getenv("TARGET_USERS_PER_BRAND", "50"))

GATEWAY_WEBHOOK_PATH = os.getenv("GATEWAY_WEBHOOK_PATH", "/webchat/webhook")
GATEWAY_WEBHOOK_SECRET = os.getenv("GATEWAY_WEBHOOK_SECRET", "dev-web")
ORCHESTRATOR_HOST = os.getenv("ORCHESTRATOR_HOST")

INGESTION_FILENAME = os.getenv("INGESTION_WARMUP_FILENAME", "warmup.md")
INGESTION_CONTENT = os.getenv(
    "INGESTION_WARMUP_CONTENT",
    "# Load Test Warmup\n\nThis document primes the ingestion workers.",
).encode("utf-8")
INGESTION_CONTENT_TYPE = os.getenv("INGESTION_WARMUP_CONTENT_TYPE", "text/markdown")


class ConversationUser(HttpUser):
    """Drive gateway → orchestrator → ingestion flows with brand tagging."""

    wait_time = between(1, 3)
    tenant_id: ClassVar[str] = TENANT_ID

    def on_start(self) -> None:
        self.brand = random.choice(BRAND_PROFILES)
        self.conversation_id = uuid4().hex
        self.sender_id = f"load-{self.conversation_id[:8]}"
        self._orchestrator_host = ORCHESTRATOR_HOST or self.host

    @task(4)
    def send_webchat_message(self) -> None:
        payload = self._build_webhook_payload()
        body = json.dumps(payload).encode("utf-8")
        correlation_id = uuid4().hex
        headers = self._gateway_headers(body, correlation_id)
        request_name = f"gateway:webhook:{self.brand.slug}"
        response = self.client.post(
            GATEWAY_WEBHOOK_PATH,
            data=body,
            headers=headers,
            name=request_name,
        )
        self._log_request(
            flow="gateway",
            correlation_id=correlation_id,
            status=response.status_code,
        )

    @task(1)
    def warmup_ingestion(self) -> None:
        if not self._orchestrator_host:
            logger.debug("skipping ingestion warmup; orchestrator host not configured")
            return

        url = f"{self._orchestrator_host}/v1/brands/{self.brand.brand_id}/knowledge"
        correlation_id = uuid4().hex
        files = {
            "file": (INGESTION_FILENAME, INGESTION_CONTENT, INGESTION_CONTENT_TYPE),
        }
        request_name = f"ingestion:warmup:{self.brand.slug}"
        response = self.client.post(
            url,
            files=files,
            headers={"X-Request-ID": correlation_id},
            name=request_name,
        )
        self._log_request(
            flow="ingestion",
            correlation_id=correlation_id,
            status=response.status_code,
        )

    def _build_webhook_payload(self) -> dict[str, object]:
        occurred_at = datetime.now(tz=UTC).isoformat()
        return {
            "event_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "brand_id": self.brand.brand_id,
            "channel_id": self.brand.channel_id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "message": "Hello from the load test",
            "locale": "en-US",
            "occurred_at": occurred_at,
            "metadata": {"load_test": True, "brand": self.brand.slug},
        }

    def _gateway_headers(self, body: bytes, correlation_id: str) -> dict[str, str]:
        signature = hmac.new(
            GATEWAY_WEBHOOK_SECRET.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return {
            "Content-Type": "application/json",
            "X-Request-ID": correlation_id,
            "X-Webchat-Signature": signature,
        }

    def _log_request(self, *, flow: str, correlation_id: str, status: int) -> None:
        logger.info(
            "load_test.request",
            extra={
                "flow": flow,
                "brand": self.brand.slug,
                "correlation_id": correlation_id,
                "status_code": status,
            },
        )
