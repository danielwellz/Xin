from __future__ import annotations

import random
from datetime import UTC, datetime
from uuid import uuid4

from locust import HttpUser, between, task

BRAND_IDS = [
    "22222222-2222-2222-2222-222222222222",
    "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
]
CHANNEL_ID = "33333333-3333-3333-3333-333333333333"
TENANT_ID = "11111111-1111-1111-1111-111111111111"
TARGET_USERS_PER_BRAND = 50


class ConversationUser(HttpUser):
    """Simulate concurrent conversations per brand hitting the orchestrator."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.brand_id = random.choice(BRAND_IDS)
        self.channel_id = CHANNEL_ID
        self.conversation_id = str(uuid4())

    @task
    def send_message(self) -> None:
        payload = {
            "id": str(uuid4()),
            "tenant_id": TENANT_ID,
            "brand_id": self.brand_id,
            "channel_id": self.channel_id,
            "conversation_id": self.conversation_id,
            "sender_id": f"load-test-{self.conversation_id[:8]}",
            "content": "Hello from load test",
            "received_at": datetime.now(tz=UTC).isoformat(),
            "locale": "en-US",
            "attachments": [],
            "metadata": {"load_test": True},
        }
        headers = {"X-Request-ID": str(uuid4())}
        self.client.post("/v1/messages/inbound", json=payload, headers=headers)
