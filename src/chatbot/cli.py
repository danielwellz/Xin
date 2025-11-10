"""Simple CLI for sending test conversations to the orchestrator API."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:  # pragma: no cover - defensive parsing branch
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interactive shell for chatting with a running orchestrator instance.",
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Base URL for the orchestrator service (default: %(default)s)",
    )
    parser.add_argument(
        "--tenant-id",
        type=_parse_uuid,
        required=True,
        help="Tenant UUID configured in the database.",
    )
    parser.add_argument(
        "--brand-id",
        type=_parse_uuid,
        required=True,
        help="Brand UUID configured in the database.",
    )
    parser.add_argument(
        "--channel-id",
        type=_parse_uuid,
        required=True,
        help="Channel configuration UUID that will be associated with messages.",
    )
    parser.add_argument(
        "--conversation-id",
        type=_parse_uuid,
        default=None,
        help="Conversation UUID to reuse between runs (default: random).",
    )
    parser.add_argument(
        "--sender-id",
        default="cli-user",
        help="Identifier for the simulated customer (default: %(default)s).",
    )
    parser.add_argument(
        "--locale",
        default="en",
        help="Locale hint passed to the orchestrator (default: %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds (default: %(default)s).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    conversation_id = args.conversation_id or uuid4()
    print("Xin Chat CLI")
    print("Press Ctrl-D to exit.\n")

    payload_template = {
        "tenant_id": str(args.tenant_id),
        "brand_id": str(args.brand_id),
        "channel_id": str(args.channel_id),
        "conversation_id": str(conversation_id),
        "sender_id": args.sender_id,
        "locale": args.locale,
    }

    with httpx.Client(base_url=args.host, timeout=args.timeout) as client:
        while True:
            try:
                message = input("You> ").strip()
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break

            if not message:
                continue

            payload = {
                **payload_template,
                "id": str(uuid4()),
                "content": message,
                "received_at": datetime.now(tz=timezone.utc).isoformat(),
            }
            response = client.post("/v1/messages/inbound", json=payload)
            if response.status_code != 202:
                print(f"! request failed ({response.status_code}): {response.text}")
                continue

            body = response.json()
            outbound = body.get("data", {}).get("outbound") or {}
            content = outbound.get("content", "").strip()
            print(f"Xin> {content}\n")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
