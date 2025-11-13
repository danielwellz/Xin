"""Async worker entrypoint for outbound dispatch loop."""

from __future__ import annotations

import asyncio
import logging

from redis.asyncio import Redis

from chatbot.core.domain import ChannelType

from .adapters.providers import (
    InstagramAdapter,
    TelegramAdapter,
    WebChatAdapter,
    WhatsAppAdapter,
)
from .dependencies import get_settings
from .outbound import OutboundStreamConsumer, RedisStreamConfig

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Run the outbound dispatcher until cancelled."""

    settings = get_settings()
    redis = Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        db=settings.redis.db,
        password=settings.redis.password,
    )

    adapters = {
        ChannelType.INSTAGRAM: InstagramAdapter(api_token=settings.instagram_token),
        ChannelType.WHATSAPP: WhatsAppAdapter(api_token=settings.whatsapp_token),
        ChannelType.TELEGRAM: TelegramAdapter(bot_token=settings.telegram_token),
        ChannelType.WEB: WebChatAdapter(),
    }

    consumer = OutboundStreamConsumer(
        redis=redis,
        adapters=adapters,
        config=RedisStreamConfig(
            key=settings.redis.stream_key,
            group=settings.redis.consumer_group,
            consumer=settings.redis.consumer_name,
        ),
    )

    await consumer.ensure_group()
    logger.info(
        "outbound worker started",
        extra={
            "stream": settings.redis.stream_key,
            "group": settings.redis.consumer_group,
        },
    )
    try:
        await consumer.poll()
    finally:
        await redis.close()
        await redis.wait_closed()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
