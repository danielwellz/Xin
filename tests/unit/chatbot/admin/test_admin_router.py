"""Unit tests covering the admin onboarding router."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from chatbot.adapters.orchestrator import dependencies
from chatbot.adapters.orchestrator.app import create_app
from chatbot.adapters.orchestrator.routers import admin as admin_router
from chatbot.admin.auth import TokenClaims


class StubStorageClient:
    def __init__(self) -> None:
        self.objects: list[tuple[str, bytes]] = []

    def store_secret_blob(
        self, *, key: str, data: bytes, content_type: str = "application/json"
    ) -> str:
        self.objects.append((key, data))
        return f"s3://test/{key}"


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.streams: list[tuple[str, dict[str, str]]] = []

    def setex(
        self, key: str, ttl: int, value: str
    ) -> None:  # pragma: no cover - trivial
        self.values[key] = value

    def xadd(self, name: str, fields: dict[str, str], **kwargs: Any) -> None:
        self.streams.append((name, fields))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    storage = StubStorageClient()
    redis = FakeRedis()

    app = create_app()
    app.dependency_overrides[dependencies.get_session] = override_session
    app.dependency_overrides[dependencies.get_storage_client] = lambda: storage
    app.dependency_overrides[dependencies.get_redis_client] = lambda: redis
    app.dependency_overrides[admin_router._get_current_claims] = lambda: TokenClaims(
        sub="tester",
        iss="xin-admin",
        aud="xin-platform",
        iat=0,
        exp=9999999999,
        roles=["platform_admin"],
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_tenant_and_channel_flow(client: TestClient) -> None:
    create_tenant = {
        "name": "Acme Support",
        "timezone": "UTC",
        "metadata": {"plan": "enterprise"},
        "embed_theme": {"primary": "#ff3366"},
    }
    tenant_response = client.post(
        "/admin/tenants", json=create_tenant, headers=auth_headers()
    )
    assert tenant_response.status_code == 201, tenant_response.text
    tenant_body = tenant_response.json()
    tenant_id = UUID(tenant_body["id"])
    assert tenant_body["embed_config"]["handshake_salt"]

    channel_payload = {
        "tenant_id": str(tenant_id),
        "brand_name": "Acme Brand",
        "channel_type": "web",
        "display_name": "Web Widget",
        "credentials": {"webhook_url": "https://example.com/xin"},
        "secret_credentials": {"api_token": "shh-very-secret"},
    }
    channel_response = client.post(
        "/admin/channels", json=channel_payload, headers=auth_headers()
    )
    assert channel_response.status_code == 201, channel_response.text
    body = channel_response.json()
    assert body["hmac_secret"], "hmac secret must be returned once"

    audit_response = client.get("/admin/audit", headers=auth_headers())
    assert audit_response.status_code == 200
    entries = audit_response.json()
    assert len(entries) >= 2

    snippet_response = client.get(
        f"/admin/embed_snippet/{tenant_id}", headers=auth_headers()
    )
    assert snippet_response.status_code == 200
    snippet = snippet_response.json()["snippet"]
    assert "embed.js" in snippet
