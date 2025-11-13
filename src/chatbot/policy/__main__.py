"""CLI for inspecting and diffing tenant policies."""

from __future__ import annotations

import argparse
import json
from uuid import UUID

import httpx


def _parse_uuid(value: str) -> UUID:
    return UUID(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Policy inspection helpers.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-token", required=True)
    parser.add_argument("--tenant-id", type=_parse_uuid, required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List policy versions.")

    diff = sub.add_parser("diff", help="Show diff for a version.")
    diff.add_argument("--version", type=int, required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    headers = {"Authorization": f"Bearer {args.api_token}"}

    with httpx.Client(base_url=args.base_url, timeout=15.0) as client:
        if args.command == "list":
            response = client.get(f"/admin/policies/{args.tenant_id}", headers=headers)
            response.raise_for_status()
            print(json.dumps(response.json(), indent=2))
        elif args.command == "diff":
            response = client.get(
                f"/admin/policies/{args.tenant_id}/diff/{args.version}",
                headers=headers,
            )
            response.raise_for_status()
            print(json.dumps(response.json(), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
