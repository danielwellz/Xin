"""Dependency wiring for the channel gateway service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from .adapters.orchestrator import OrchestratorClient, OrchestratorClientSettings
from .adapters.providers import (
    InstagramAdapter,
    TelegramAdapter,
    WebChatAdapter,
    WhatsAppAdapter,
)
from .settings import ChannelGatewaySettings


@lru_cache(maxsize=1)
def get_settings() -> ChannelGatewaySettings:
    return ChannelGatewaySettings()


SettingsDep = Annotated[ChannelGatewaySettings, Depends(get_settings)]


async def get_redis(settings: SettingsDep) -> AsyncIterator[Redis]:
    client = Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        db=settings.redis.db,
        password=settings.redis.password,
    )
    try:
        yield client
    finally:
        await client.close()
        await client.wait_closed()


_orchestrator_client: OrchestratorClient | None = None


def get_orchestrator_client(settings: SettingsDep) -> OrchestratorClient:
    global _orchestrator_client
    if _orchestrator_client is None:
        _orchestrator_client = OrchestratorClient(
            settings=OrchestratorClientSettings(base_url=str(settings.orchestrator_url)),
        )
    return _orchestrator_client


def get_instagram_adapter(settings: SettingsDep) -> InstagramAdapter:
    return InstagramAdapter(api_token=settings.instagram_token)


def get_whatsapp_adapter(settings: SettingsDep) -> WhatsAppAdapter:
    return WhatsAppAdapter(api_token=settings.whatsapp_token)


def get_telegram_adapter(settings: SettingsDep) -> TelegramAdapter:
    return TelegramAdapter(bot_token=settings.telegram_token)


def get_web_adapter(_: SettingsDep) -> WebChatAdapter:
    return WebChatAdapter()
