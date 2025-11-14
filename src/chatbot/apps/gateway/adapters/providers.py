"""Provider SDK adapter interfaces and stub implementations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from chatbot.core.domain import OutboundResponse

logger = logging.getLogger(__name__)


class ProviderAdapter(Protocol):
    """Interface implemented by messaging provider adapters."""

    async def send(self, response: OutboundResponse) -> None:
        ...


@dataclass(slots=True)
class InstagramAdapter:
    """Adapter wrapping Instagram messaging SDK."""

    api_token: str

    async def send(self, response: OutboundResponse) -> None:
        logger.info(
            "sending instagram response",
            extra={
                "conversation": str(response.conversation_id),
                "content": response.content,
            },
        )


@dataclass(slots=True)
class WhatsAppAdapter:
    """Adapter wrapping WhatsApp Business API."""

    api_token: str

    async def send(self, response: OutboundResponse) -> None:
        logger.info(
            "sending whatsapp response",
            extra={
                "conversation": str(response.conversation_id),
                "content": response.content,
            },
        )


@dataclass(slots=True)
class TelegramAdapter:
    """Adapter wrapping Telegram Bot API."""

    bot_token: str

    async def send(self, response: OutboundResponse) -> None:
        logger.info(
            "sending telegram response",
            extra={
                "conversation": str(response.conversation_id),
                "content": response.content,
            },
        )


@dataclass(slots=True)
class WebChatAdapter:
    """Adapter delivering responses to the web chat channel."""

    async def send(self, response: OutboundResponse) -> None:
        logger.info(
            "sending web chat response",
            extra={
                "conversation": str(response.conversation_id),
                "content": response.content,
            },
        )
