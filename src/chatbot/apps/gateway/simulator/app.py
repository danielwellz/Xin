"""Local callback simulator for channel webhooks."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ChannelGatewaySettings

REPO_ROOT = Path(__file__).resolve().parents[6]
FIXTURE_DIR = REPO_ROOT / "tests" / "unit" / "channel_gateway" / "fixtures"


class SimulatorSettings(BaseSettings):
    """Environment for the simulator process."""

    model_config = SettingsConfigDict(
        env_prefix="SIM_", env_file=(".env.local", ".env"), case_sensitive=False
    )

    target_url: AnyHttpUrl = "http://localhost:8080"


app = FastAPI(title="Channel Gateway Simulator", version="0.1.0")
settings = SimulatorSettings()
channel_settings = ChannelGatewaySettings()


@app.get("/scenarios")
async def list_scenarios() -> dict[str, list[str]]:
    fixtures = [fixture.stem for fixture in FIXTURE_DIR.glob("*.json")]
    return {"scenarios": sorted(fixtures)}


@app.post("/callbacks/{channel}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_callback(channel: str) -> dict[str, Any]:
    fixture_path = FIXTURE_DIR / f"{channel}_message.json"
    if not fixture_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="fixture not found"
        )

    payload = json.loads(fixture_path.read_text())
    headers = _build_headers(channel, payload)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.target_url}/{_channel_prefix(channel)}/webhook",
            json=payload,
            headers=headers,
        )

    return {"status": response.status_code, "body": _safe_json(response)}


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _channel_prefix(channel: str) -> str:
    mapping = {
        "instagram": "instagram",
        "whatsapp": "whatsapp",
        "telegram": "telegram",
        "web": "webchat",
    }
    if channel not in mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="unknown channel"
        )
    return mapping[channel]


def _build_headers(channel: str, payload: dict[str, Any]) -> dict[str, str]:
    body = json.dumps(payload).encode("utf-8")
    headers: dict[str, str] = {}

    if channel == "instagram":
        digest = hmac.new(
            channel_settings.instagram_secret.encode("utf-8"), body, hashlib.sha1
        ).hexdigest()
        headers["X-Hub-Signature"] = f"sha1={digest}"
    elif channel == "whatsapp":
        digest = hmac.new(
            channel_settings.whatsapp_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        headers["X-WHATSAPP-SIGNATURE"] = digest
    elif channel == "telegram":
        headers["X-Telegram-Secret-Token"] = channel_settings.telegram_secret
    elif channel == "web":
        digest = hmac.new(
            channel_settings.web_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        headers["X-Webchat-Signature"] = digest
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="unknown channel"
        )

    return headers


def main() -> None:
    import uvicorn

    uvicorn.run(
        "chatbot.apps.gateway.simulator.app:app",
        host="127.0.0.1",
        port=8085,
        reload=False,
    )


if __name__ == "__main__":
    main()
