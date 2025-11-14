"""Integration tests for the orchestrator FastAPI service."""

from __future__ import annotations

import time
from collections.abc import Generator
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
import psycopg2
from redis import Redis
from sqlmodel import Session, select
from testcontainers.core.container import DockerContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from chatbot.core.db import models as db_models
from chatbot.core.db.session import init_db
from chatbot.apps.orchestrator import dependencies
from chatbot.apps.orchestrator.app import create_app
from chatbot.core.storage import StorageUploadResult

pytestmark = pytest.mark.integration


class StubStorageClient:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str]] = []

    def upload_document(self, **kwargs):
        tenant_id = kwargs["tenant_id"]
        brand_id = kwargs["brand_id"]
        knowledge_id = kwargs["knowledge_id"]
        filename = kwargs.get("filename") or "upload"
        key = f"{tenant_id}/{brand_id}/{knowledge_id}/{filename}"
        self.uploads.append((str(knowledge_id), key))
        return StorageUploadResult(uri=f"s3://test/{key}", key=key, filename=filename)


class StubIngestionPublisher:
    def __init__(self) -> None:
        self.jobs: list[object] = []

    async def enqueue_job(self, registration):
        self.jobs.append(registration)
        return str(registration.knowledge.id)

    async def close(self) -> None:
        return None


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:15-alpine") as container:
        container.start()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                connection = psycopg2.connect(
                    host=container.get_container_host_ip(),
                    port=int(container.get_exposed_port("5432")),
                    user=container.POSTGRES_USER,
                    password=container.POSTGRES_PASSWORD,
                    dbname=container.POSTGRES_DB,
                )
                connection.autocommit = True
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s", ("chatbot",)
                    )
                    if cursor.fetchone() is None:
                        cursor.execute("CREATE DATABASE chatbot")
                connection.close()
                break
            except psycopg2.OperationalError:
                time.sleep(1)
        else:
            raise RuntimeError("Postgres container failed to become ready within 30s")
        yield container


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    with RedisContainer("redis:7.2-alpine") as container:
        container.start()
        yield container


@pytest.fixture(scope="session")
def qdrant_container() -> Generator[DockerContainer, None, None]:
    container = DockerContainer("qdrant/qdrant:v1.8.2").with_exposed_ports("6333/tcp")
    container.start()

    host = container.get_container_host_ip()
    port = container.get_exposed_port("6333")
    base_url = f"http://{host}:{port}"

    def _is_ready() -> bool:
        try:
            response = httpx.get(f"{base_url}/readyz", timeout=2.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if _is_ready():
            break
        time.sleep(1)
    else:
        raise RuntimeError("Qdrant container failed to become ready within 30s")
    yield container
    container.stop()


@pytest.fixture()
def test_client(
    postgres_container: PostgresContainer,
    redis_container: RedisContainer,
    qdrant_container: DockerContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    postgres_host = postgres_container.get_container_host_ip()
    postgres_port = postgres_container.get_exposed_port("5432")
    monkeypatch.setenv("POSTGRES_HOST", postgres_host)
    monkeypatch.setenv("POSTGRES_PORT", postgres_port)
    monkeypatch.setenv("POSTGRES_DATABASE", postgres_container.POSTGRES_DB)
    monkeypatch.setenv("POSTGRES_USER", postgres_container.POSTGRES_USER)
    monkeypatch.setenv("POSTGRES_PASSWORD", postgres_container.POSTGRES_PASSWORD)
    monkeypatch.setenv("POSTGRES_SSLMODE", "disable")

    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port("6379")
    monkeypatch.setenv("REDIS_URL", f"redis://{redis_host}:{redis_port}/0")

    qdrant_host = qdrant_container.get_container_host_ip()
    qdrant_port = qdrant_container.get_exposed_port("6333")
    monkeypatch.setenv("QDRANT_URL", f"http://{qdrant_host}:{qdrant_port}")
    monkeypatch.setenv("QDRANT_TIMEOUT_SECONDS", "5")

    dependencies.get_settings.cache_clear()
    dependencies.get_engine.cache_clear()
    dependencies.get_embedding_service.cache_clear()
    dependencies.get_vector_store.cache_clear()
    dependencies.get_redis_client.cache_clear()
    dependencies.get_llm_client.cache_clear()
    dependencies.get_guardrail_service.cache_clear()
    dependencies.get_storage_client.cache_clear()
    dependencies.get_ingestion_job_publisher.cache_clear()

    # Flush any existing engines created with prior settings.
    from chatbot.core.db import session as db_session_module

    db_session_module._ENGINE_CACHE.clear()  # type: ignore[attr-defined]

    app = create_app()
    storage_stub = StubStorageClient()
    ingestion_stub = StubIngestionPublisher()
    app.dependency_overrides[dependencies.get_storage_client] = lambda: storage_stub
    app.dependency_overrides[dependencies.get_ingestion_job_publisher] = (
        lambda: ingestion_stub
    )
    app.state.test_storage = storage_stub
    app.state.test_ingestion_publisher = ingestion_stub
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    client.close()


@pytest.fixture()
def seeded_database() -> Generator[dict[str, object], None, None]:
    engine = dependencies.get_engine()
    db_models.metadata.drop_all(engine)
    init_db(engine)

    tenant_id = uuid4()
    brand_id = uuid4()
    channel_id = uuid4()

    with Session(engine) as session:
        tenant = db_models.Tenant(id=tenant_id, name="Acme Co", timezone="UTC")
        brand = db_models.Brand(
            id=brand_id,
            tenant_id=tenant_id,
            name="Acme Support",
            slug="acme-support",
            language="en",
        )
        channel = db_models.ChannelConfig(
            id=channel_id,
            brand_id=brand_id,
            channel_type=db_models.ChannelType.WEB,
            display_name="Web",
        )
        persona = db_models.PersonaProfile(
            brand_id=brand_id,
            name="Default Persona",
            prompt_template="You are Acme Support assistant. Keep answers concise.",
        )

        session.add(tenant)
        session.add(brand)
        session.add(channel)
        session.add(persona)
        session.commit()

    redis_client = dependencies.get_redis_client()
    if isinstance(redis_client, Redis):
        redis_client.flushall()

    yield {
        "tenant_id": tenant_id,
        "brand_id": brand_id,
        "channel_id": channel_id,
    }


def _redis() -> Redis:
    client = dependencies.get_redis_client()
    assert isinstance(client, Redis)
    return client


def test_post_inbound_message_generates_response(
    test_client: TestClient,
    seeded_database: dict[str, object],
) -> None:
    conversation_id = uuid4()
    payload = {
        "id": str(uuid4()),
        "tenant_id": str(seeded_database["tenant_id"]),
        "brand_id": str(seeded_database["brand_id"]),
        "channel_id": str(seeded_database["channel_id"]),
        "conversation_id": str(conversation_id),
        "sender_id": "user-123",
        "content": "Hello, I need help with my order.",
        "locale": "en",
    }

    response = test_client.post("/v1/messages/inbound", json=payload)
    assert response.status_code == 202, response.text

    body = response.json()
    assert body["data"]["conversation_id"] == str(conversation_id)
    assert "content" in body["data"]["outbound"]

    engine = dependencies.get_engine()
    with Session(engine) as session:
        logs = session.exec(
            select(db_models.MessageLog).where(
                db_models.MessageLog.conversation_id == conversation_id
            )
        ).all()
        assert len(logs) == 2

    redis_client = _redis()
    time.sleep(0.1)  # ensure stream write propagates
    entries = redis_client.xrange("outbound:messages")
    assert entries, "expected outbound entry in redis stream"


def test_upload_knowledge_creates_source_and_enqueues_job(
    test_client: TestClient,
    seeded_database: dict[str, object],
) -> None:
    brand_id = seeded_database["brand_id"]
    files = {
        "file": ("faq.md", b"# FAQ\n\nQ: Test?\nA: Yes!", "text/markdown"),
    }
    response = test_client.post(f"/v1/brands/{brand_id}/knowledge", files=files)
    assert response.status_code == 202, response.text

    body = response.json()
    knowledge_id = body["data"]["knowledge_source_id"]

    engine = dependencies.get_engine()
    with Session(engine) as session:
        knowledge = session.get(db_models.KnowledgeSource, knowledge_id)
        assert knowledge is not None
        assert knowledge.status == db_models.KnowledgeSourceStatus.PENDING

    storage_stub: StubStorageClient = test_client.app.state.test_storage
    ingestion_stub: StubIngestionPublisher = (
        test_client.app.state.test_ingestion_publisher
    )
    assert storage_stub.uploads, "expected object storage upload"
    assert ingestion_stub.jobs, "expected ingestion job to be enqueued"
    assert str(ingestion_stub.jobs[0].knowledge.id) == knowledge_id


def test_get_conversation_returns_history(
    test_client: TestClient,
    seeded_database: dict[str, object],
) -> None:
    conversation_id = uuid4()
    payload = {
        "id": str(uuid4()),
        "tenant_id": str(seeded_database["tenant_id"]),
        "brand_id": str(seeded_database["brand_id"]),
        "channel_id": str(seeded_database["channel_id"]),
        "conversation_id": str(conversation_id),
        "sender_id": "user-999",
        "content": "Test conversation history",
        "locale": "en",
    }

    post_response = test_client.post("/v1/messages/inbound", json=payload)
    assert post_response.status_code == 202

    response = test_client.get(f"/v1/conversations/{conversation_id}")
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["data"]["conversation_id"] == str(conversation_id)
    assert len(body["data"]["messages"]) >= 2
