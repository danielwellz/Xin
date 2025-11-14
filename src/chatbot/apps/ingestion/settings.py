"""Environment configuration for the ingestion worker."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from chatbot.core.config import LLMProvider
from chatbot.rag.embeddings import EmbeddingSettings


class IngestionWorkerSettings(BaseSettings):
    """Configuration sourced from environment variables or .env files."""

    model_config = SettingsConfigDict(
        env_prefix="INGEST_", env_file=(".env.local", ".env"), case_sensitive=False
    )

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_progress_channel_template: str = "ingestion:{tenant}:{brand}"
    redis_poison_key: str = "ingestion:poison"
    redis_queue_name: str = "ingestion"

    arq_concurrency: int = 5
    arq_job_timeout: int = 60 * 10
    arq_max_retries: int = 5
    backoff_base: float = 2.0
    backoff_factor: float = 2.0
    backoff_max: float = 60.0

    postgres_dsn: str

    minio_endpoint_url: str = "http://localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_region: str = "us-east-1"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_prefix: str = "knowledge"
    qdrant_vector_size: int = 1536

    embedding_provider: LLMProvider = LLMProvider.OPENAI
    embedding_openai_model: str = "text-embedding-3-large"
    embedding_openai_key: str | None = None
    embedding_sentence_transformer: str = "sentence-transformers/all-MiniLM-L6-v2"

    otlp_endpoint: str | None = None
    otlp_headers: str | None = None
    metrics_host: str = "0.0.0.0"
    metrics_port: int | None = 9103

    def embedding_settings(self) -> EmbeddingSettings:
        return EmbeddingSettings(
            provider=self.embedding_provider,
            openai_model=self.embedding_openai_model,
            openai_api_key=self.embedding_openai_key,
            sentence_transformer_model=self.embedding_sentence_transformer,
        )
