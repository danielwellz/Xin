"""Client for forwarding inbound messages to the orchestrator service."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from chatbot.core.domain import InboundMessage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OrchestratorClientSettings:
    """Configuration for orchestrator client."""

    base_url: str
    timeout: float = 5.0


class OrchestratorClient:
    """Forward inbound messages to the orchestrator HTTP API."""

    def __init__(self, *, settings: OrchestratorClientSettings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(base_url=settings.base_url, timeout=settings.timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def forward_inbound(self, message: InboundMessage) -> None:
        payload = {
            "id": str(message.id),
            "tenant_id": str(message.tenant_id),
            "brand_id": str(message.brand_id),
            "channel_id": str(message.channel_id),
            "conversation_id": str(message.conversation_id),
            "sender_id": message.sender_id,
            "content": message.content,
            "received_at": message.received_at.isoformat(),
            "locale": message.locale,
            "attachments": message.attachments,
            "metadata": message.metadata,
        }
        try:
            response = await self._client.post("/v1/messages/inbound", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error(
                "orchestrator rejected inbound message",
                extra={"status": exc.response.status_code, "body": body},
            )
            raise
        except httpx.HTTPError:
            logger.exception("failed to send inbound message to orchestrator")
            raise
