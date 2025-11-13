"""Automation CLI utilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

import httpx


def _parse_uuid(value: str) -> UUID:
    return UUID(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automation rule utilities.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-token", required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    simulate = sub.add_parser("simulate", help="Dry-run an automation rule action.")
    simulate.add_argument("--tenant-id", type=_parse_uuid, required=True)
    simulate.add_argument("--rule-id", type=_parse_uuid, required=True)

    sub.add_parser("rules", help="List automation rules (platform scope).")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    headers = {"Authorization": f"Bearer {args.api_token}"}

    with httpx.Client(base_url=args.base_url, timeout=15.0) as client:
        if args.command == "rules":
            response = client.get("/admin/automation/rules", headers=headers)
            response.raise_for_status()
            print(json.dumps(response.json(), indent=2))
        elif args.command == "simulate":
            response = client.get(
                "/admin/automation/rules",
                headers=headers,
                params={"tenant_id": str(args.tenant_id)},
            )
            response.raise_for_status()
            rules = response.json()
            match = next(
                (rule for rule in rules if rule["id"] == str(args.rule_id)), None
            )
            if not match:
                raise SystemExit("Rule not found for tenant")
            payload = {
                "rule": match,
                "sample_payload": match.get("action_payload"),
            }
            resp = client.post("/admin/automation/test", headers=headers, json=payload)
            resp.raise_for_status()
            print(json.dumps(resp.json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
