from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "unit" / "channel_gateway" / "fixtures"

pytestmark = pytest.mark.contract


@pytest.mark.parametrize(
    "fixture_name",
    [
        "instagram",
        "whatsapp",
        "telegram",
        "web",
    ],
)
def test_fixture_contains_required_fields(fixture_name: str) -> None:
    payload = json.loads((FIXTURE_DIR / f"{fixture_name}_message.json").read_text())

    required_fields = {"tenant_id", "brand_id", "channel_id", "sender_id", "event_id"}
    missing = sorted(required_fields - payload.keys())
    assert not missing, f"Missing fields in {fixture_name}: {missing}"

    assert payload.get("message") or payload.get("text"), "payload must include message content"
