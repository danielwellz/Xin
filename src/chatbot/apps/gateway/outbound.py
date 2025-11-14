"""Redis stream consumer dispatching outbound responses to providers."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis

from chatbot.core.domain import ChannelType, OutboundResponse

from .adapters.providers import ProviderAdapter
from .utils.exceptions import ProviderDispatchError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RedisStreamConfig:
    key: str
    group: str
    consumer: str
    block_ms: int = 1_000
    count: int = 10


class OutboundStreamConsumer:
    """Consume outbound messages from Redis streams and dispatch them."""

    def __init__(
        self,
        *,
        redis: Redis,
        adapters: Mapping[ChannelType, ProviderAdapter],
        config: RedisStreamConfig,
    ) -> None:
        self._redis = redis
        self._adapters = adapters
        self._config = config

    async def ensure_group(self) -> None:
        """Ensure the consumer group exists."""

        try:
            await self._redis.xgroup_create(
                name=self._config.key,
                groupname=self._config.group,
                id="$",
                mkstream=True,
            )
        except Exception:  # pragma: no cover - group likely exists
            pass

    async def poll(self) -> None:
        """Continuously poll the Redis stream until cancelled."""

        await self.ensure_group()
        while True:
            entries = await self._redis.xreadgroup(
                groupname=self._config.group,
                consumername=self._config.consumer,
                streams={self._config.key: ">"},
                count=self._config.count,
                block=self._config.block_ms,
            )

            if not entries:
                continue

            for _, messages in entries:
                for message_id, raw_fields in messages:
                    await self._process_entry(message_id, raw_fields)

    async def _process_entry(
        self, message_id: str, raw_fields: Mapping[bytes, bytes]
    ) -> None:
        try:
            response, channel_type = _decode_outbound_response(raw_fields)
            adapter = self._adapters.get(channel_type)
            if adapter is None:
                raise ProviderDispatchError(
                    f"no adapter configured for channel {channel_type.value}"
                )

            await adapter.send(response)
            await self._redis.xack(self._config.key, self._config.group, message_id)
        except ProviderDispatchError:
            logger.exception(
                "failed to dispatch outbound message", extra={"message_id": message_id}
            )
            await self._redis.xack(self._config.key, self._config.group, message_id)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception(
                "unexpected error processing outbound message",
                extra={"message_id": message_id},
            )


def _decode_outbound_response(
    raw_fields: Mapping[bytes, bytes],
) -> tuple[OutboundResponse, ChannelType]:
    payload = {}
    for key, value in raw_fields.items():
        payload[key.decode("utf-8")] = value.decode("utf-8")

    metadata = json.loads(payload.get("metadata", "{}"))
    channel_type_str = metadata.get("channel_type")
    channel_type = (
        ChannelType(channel_type_str) if channel_type_str else ChannelType.WEB
    )

    created_at_str = payload.get("created_at")
    if created_at_str:
        created_at = datetime.fromisoformat(created_at_str)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
    else:
        created_at = datetime.now(tz=UTC)

    response = OutboundResponse(
        id=UUID(payload["id"]),
        tenant_id=UUID(payload["tenant_id"]),
        brand_id=UUID(payload["brand_id"]),
        channel_id=UUID(payload["channel_id"]),
        conversation_id=UUID(payload["conversation_id"]),
        content=payload["content"],
        created_at=created_at,
        metadata=metadata,
    )
    return response, channel_type
