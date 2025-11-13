#!/usr/bin/env python
"""Demo script that provisions a tenant + channel through the admin API."""

from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx


def _request(
    client: httpx.Client,
    method: str,
    url: str,
    token: str,
    **kwargs: Any,
) -> dict[str, Any]:
    response = client.request(method, url, headers={"Authorization": f"Bearer {token}"}, **kwargs)
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision a demo tenant + channel via admin API.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Orchestrator base URL.")
    parser.add_argument("--api-token", required=True, help="Admin JWT with platform_admin scope.")
    parser.add_argument("--tenant-name", default="Demo Tenant")
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument("--brand-name", default="Demo Brand")
    parser.add_argument(
        "--channel-type",
        default="web",
        choices=["web", "instagram", "telegram", "whatsapp"],
    )
    parser.add_argument("--channel-name", default="Demo Web")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    token = args.api_token

    with httpx.Client(timeout=10.0) as client:
        tenant_payload = {
            "name": args.tenant_name,
            "timezone": args.timezone,
            "metadata": {"plan": "demo"},
        }
        tenant = _request(client, "POST", f"{base_url}/admin/tenants", token, json=tenant_payload)
        tenant_id = tenant["id"]
        print(f"✅ Created tenant {tenant['name']} ({tenant_id})")

        channel_payload = {
            "tenant_id": tenant_id,
            "brand_name": args.brand_name,
            "channel_type": args.channel_type,
            "display_name": args.channel_name,
            "credentials": {"webhook_url": f"https://example.com/hooks/{tenant_id}"},
        }
        channel = _request(client, "POST", f"{base_url}/admin/channels", token, json=channel_payload)
        print(f"✅ Provisioned channel {channel['display_name']} with id {channel['id']}")
        print(f"   Store this HMAC secret securely: {channel['hmac_secret']}")

        snippet = _request(
            client,
            "GET",
            f"{base_url}/admin/embed_snippet/{tenant_id}",
            token,
        )
        print("\nEmbed snippet:\n")
        print(snippet["snippet"])

        audit = _request(client, "GET", f"{base_url}/admin/audit", token, params={"tenant_id": tenant_id})
        print(f"\nAudit trail contains {len(audit)} entries.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
