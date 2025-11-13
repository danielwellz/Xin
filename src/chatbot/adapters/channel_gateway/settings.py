"""Environment configuration for the channel gateway service."""

from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    stream_key: str = "outbound:messages"
    consumer_group: str = "channel_gateway"
    consumer_name: str = "gateway_worker"


class ChannelGatewaySettings(BaseSettings):
    """Top-level configuration loaded from environment."""

    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_", env_file=".env", case_sensitive=False
    )

    app_version: str = "0.1.0"
    orchestrator_url: AnyHttpUrl = "http://localhost:8001"

    instagram_secret: str = "dev-instagram"
    whatsapp_secret: str = "dev-whatsapp"
    telegram_secret: str = "dev-telegram"
    web_secret: str = "dev-web"

    instagram_token: str = "insta-token"
    whatsapp_token: str = "wa-token"
    telegram_token: str = "telegram-token"

    redis: RedisSettings = RedisSettings()

    otlp_endpoint: str | None = None
    otlp_headers: str | None = None
    metrics_host: str = "0.0.0.0"
    metrics_port: int | None = 9102
