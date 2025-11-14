from __future__ import annotations

import json
from uuid import uuid4

import pytest

from chatbot.apps.gateway.outbound import (
    OutboundStreamConsumer,
    RedisStreamConfig,
)
from chatbot.core.domain import ChannelType

pytestmark = pytest.mark.unit


class StubRedis:
    def __init__(self) -> None:
        self.acked: list[tuple[str, str, str]] = []

    async def xack(self, key: str, group: str, message_id: str) -> None:
        self.acked.append((key, group, message_id))

    async def xgroup_create(self, *args, **kwargs):  # noqa: ANN001 - signature shaped for test usage
        return None


class StubAdapter:
    def __init__(self) -> None:
        self.sent = []

    async def send(self, response):  # noqa: ANN001 - generic stub signature
        self.sent.append(response)


@pytest.mark.asyncio
async def test_process_entry_dispatches_to_provider():
    redis = StubRedis()
    adapter = StubAdapter()
    consumer = OutboundStreamConsumer(
        redis=redis,
        adapters={ChannelType.INSTAGRAM: adapter},
        config=RedisStreamConfig(key="outbound", group="gateway", consumer="worker"),
    )

    message_id = "1-0"
    payload = {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "brand_id": str(uuid4()),
        "channel_id": str(uuid4()),
        "conversation_id": str(uuid4()),
        "content": "hello",
        "metadata": json.dumps({"channel_type": "instagram"}),
    }
    fields = {
        key.encode("utf-8"): value.encode("utf-8") for key, value in payload.items()
    }

    await consumer._process_entry(message_id, fields)

    assert adapter.sent
    assert redis.acked == [("outbound", "gateway", message_id)]


@pytest.mark.asyncio
async def test_process_entry_acknowledges_unknown_channel():
    redis = StubRedis()
    adapter = StubAdapter()
    consumer = OutboundStreamConsumer(
        redis=redis,
        adapters={ChannelType.WEB: adapter},
        config=RedisStreamConfig(key="outbound", group="gateway", consumer="worker"),
    )

    message_id = "2-0"
    payload = {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "brand_id": str(uuid4()),
        "channel_id": str(uuid4()),
        "conversation_id": str(uuid4()),
        "content": "missing adapter",
        "metadata": json.dumps({"channel_type": "instagram"}),
    }
    fields = {
        key.encode("utf-8"): value.encode("utf-8") for key, value in payload.items()
    }

    await consumer._process_entry(message_id, fields)

    assert not adapter.sent
    assert redis.acked == [("outbound", "gateway", message_id)]
