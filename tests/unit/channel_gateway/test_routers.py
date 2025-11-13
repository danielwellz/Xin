from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient

from chatbot.adapters.channel_gateway import dependencies as deps
from chatbot.adapters.channel_gateway.app import create_app
from chatbot.adapters.channel_gateway.dependencies import (
    get_orchestrator_client,
    get_settings,
)
from chatbot.adapters.channel_gateway.settings import ChannelGatewaySettings


class StubOrchestratorClient:
    def __init__(self) -> None:
        self.messages = []

    async def forward_inbound(self, message) -> None:  # noqa: ANN001 - generic stub signature
        self.messages.append(message)

    async def close(self) -> None:
        return None


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{name}_message.json").read_text())


@pytest.fixture
def test_app():
    deps.get_settings.cache_clear()
    deps._orchestrator_client = None

    settings = ChannelGatewaySettings(
        orchestrator_url="http://orchestrator.local",
        instagram_secret="instagram-secret",
        whatsapp_secret="whatsapp-secret",
        telegram_secret="telegram-secret",
        web_secret="web-secret",
    )

    stub = StubOrchestratorClient()

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_orchestrator_client] = lambda: stub

    yield app, settings, stub

    app.dependency_overrides.clear()


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_instagram_webhook_forwards_message(test_app):
    app, settings, orchestrator = test_app
    payload = load_fixture("instagram")
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(
        settings.instagram_secret.encode("utf-8"), body, hashlib.sha1
    ).hexdigest()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/instagram/webhook",
            content=body,
            headers={"X-Hub-Signature": f"sha1={signature}"},
        )

    assert response.status_code == 202
    assert orchestrator.messages
    message = orchestrator.messages[0]
    assert message.content == payload["message"]
    assert message.tenant_id == UUID(payload["tenant_id"])


@pytest.mark.asyncio
async def test_instagram_webhook_rejects_bad_signature(test_app):
    app, _, _ = test_app
    payload = load_fixture("instagram")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/instagram/webhook",
            json=payload,
            headers={"X-Hub-Signature": "sha1=invalid"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_whatsapp_webhook_forwards_message(test_app):
    app, settings, orchestrator = test_app
    payload = load_fixture("whatsapp")
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(
        settings.whatsapp_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/whatsapp/webhook",
            content=body,
            headers={"X-WHATSAPP-SIGNATURE": signature},
        )

    assert response.status_code == 202
    assert orchestrator.messages
    assert orchestrator.messages[-1].content == payload["message"]


@pytest.mark.asyncio
async def test_telegram_webhook_forwards_message(test_app):
    app, settings, orchestrator = test_app
    payload = load_fixture("telegram")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/telegram/webhook",
            json=payload,
            headers={"X-Telegram-Secret-Token": settings.telegram_secret},
        )

    assert response.status_code == 202
    assert orchestrator.messages
    assert orchestrator.messages[-1].content == payload["text"]


@pytest.mark.asyncio
async def test_webchat_webhook_forwards_message(test_app):
    app, settings, orchestrator = test_app
    payload = load_fixture("web")
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(
        settings.web_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webchat/webhook",
            content=body,
            headers={"X-Webchat-Signature": signature},
        )

    assert response.status_code == 202
    assert orchestrator.messages
    assert orchestrator.messages[-1].content == payload["message"]
