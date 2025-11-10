"""Configuration loaders for the core services.

Leverages pydantic-settings to hydrate runtime configuration from environment
variables, an optional ``.env`` file, or default values. Nested settings classes
mirror infrastructure concerns (datastore, vector store, LLM providers).
"""

from __future__ import annotations

from enum import Enum
from functools import cached_property
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base settings that looks at environment variables and an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class PostgresSettings(BaseAppSettings):
    """Postgres connection details."""

    model_config = SettingsConfigDict(
        env_prefix="postgres_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(
        default="chatbot",
        validation_alias=AliasChoices("database", "db"),
    )
    user: str = "chatbot"
    password: str = "changeme"
    sslmode: str = "prefer"

    @cached_property
    def dsn(self) -> str:
        """Return a libpq compatible DSN string."""

        return (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.sslmode}"
        )


class RedisSettings(BaseAppSettings):
    """Redis URL configuration for streams and task queues."""

    model_config = SettingsConfigDict(
        env_prefix="redis_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = "redis://localhost:6379/0"


class QdrantSettings(BaseAppSettings):
    """Qdrant vector store configuration."""

    model_config = SettingsConfigDict(
        env_prefix="qdrant_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = "http://localhost:6333"
    api_key: str | None = None
    timeout_seconds: float = Field(default=10.0, ge=0.1)


class LLMProvider(str, Enum):
    """Supported LLM provider identifiers."""

    OPENAI = "openai"
    OPENROUTER = "openrouter"


class OpenAISettings(BaseAppSettings):
    """Configuration specific to OpenAI-compatible models."""

    model_config = SettingsConfigDict(
        env_prefix="openai_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str | None = None
    model: str = Field(default="gpt-4.1-mini")
    embedding_model: str = Field(default="text-embedding-3-large")
    timeout_seconds: float = Field(default=30.0, ge=0.1)


class OpenRouterSettings(BaseAppSettings):
    """Configuration specific to OpenRouter-hosted models."""

    model_config = SettingsConfigDict(
        env_prefix="openrouter_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: float = Field(default=30.0, ge=0.1)


class LLMSettings(BaseAppSettings):
    """Aggregate configuration for the active LLM provider."""

    model_config = SettingsConfigDict(
        env_prefix="llm_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    provider: LLMProvider = LLMProvider.OPENAI
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)

    def resolve_credentials(
        self,
        openai: OpenAISettings,
        openrouter: OpenRouterSettings,
    ) -> dict[str, Any]:
        """Return the credential payload for the configured provider."""

        if self.provider is LLMProvider.OPENAI:
            return {
                "api_key": openai.api_key,
                "model": openai.model,
                "embedding_model": openai.embedding_model,
                "timeout_seconds": openai.timeout_seconds,
            }

        return {
            "api_key": openrouter.api_key,
            "base_url": openrouter.base_url,
            "timeout_seconds": openrouter.timeout_seconds,
        }


class TelemetrySettings(BaseAppSettings):
    """Shared telemetry configuration."""

    model_config = SettingsConfigDict(
        env_prefix="otel_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    exporter_endpoint: str | None = None
    exporter_headers: str | None = None
    metrics_host: str = "0.0.0.0"
    metrics_port: int | None = None


class StorageSettings(BaseAppSettings):
    """Object storage configuration for knowledge uploads."""

    model_config = SettingsConfigDict(
        env_prefix="storage_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    endpoint_url: str = "http://localhost:9000"
    bucket: str = "knowledge"
    access_key: str = "minio"
    secret_key: str = "minio123"
    region: str = "us-east-1"


class IngestionQueueSettings(BaseAppSettings):
    """Redis connection details for the ingestion worker queue."""

    model_config = SettingsConfigDict(
        env_prefix="ingest_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    redis_host: str = "localhost"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0)
    redis_password: str | None = None
    queue_name: str = "ingestion"


class AppSettings(BaseAppSettings):
    """Top level settings object used by services."""

    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    ingestion_queue: IngestionQueueSettings = Field(default_factory=IngestionQueueSettings)

    @classmethod
    def load(cls, **kwargs: Any) -> AppSettings:
        """Helper factory that mirrors BaseSettings semantics."""

        return cls(**kwargs)
