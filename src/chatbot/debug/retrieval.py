"""CLI diagnostics for retrieval context."""

from __future__ import annotations

import argparse
import json
from uuid import UUID

import httpx


def _parse_uuid(value: str) -> UUID:
    return UUID(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect retrieval hits for a query.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-token", required=True)
    parser.add_argument("--tenant-id", type=_parse_uuid, required=True)
    parser.add_argument("--brand-id", type=_parse_uuid, required=True)
    parser.add_argument("--channel-id", type=_parse_uuid, required=False)
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-docs", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    headers = {"Authorization": f"Bearer {args.api_token}"}

    payload = {
        "tenant_id": str(args.tenant_id),
        "brand_id": str(args.brand_id),
        "message": args.query,
        "max_documents": args.max_docs,
    }
    if args.channel_id:
        payload["channel_id"] = str(args.channel_id)

    with httpx.Client(base_url=args.base_url, timeout=20.0) as client:
        response = client.post(
            "/admin/diagnostics/retrieval",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
