"""CLI helper for administering knowledge ingestion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx


def _parse_uuid(value: str) -> UUID:
    return UUID(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upload and track knowledge ingestion jobs."
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Orchestrator base URL."
    )
    parser.add_argument(
        "--api-token", required=True, help="Admin JWT with platform scope."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    upload = sub.add_parser("upload", help="Upload a document and enqueue ingestion.")
    upload.add_argument("--tenant-id", type=_parse_uuid, required=True)
    upload.add_argument("--brand-id", type=_parse_uuid, required=True)
    upload.add_argument("--file", type=Path, required=True)
    upload.add_argument(
        "--visibility", choices=["private", "tenant", "public"], default="private"
    )
    upload.add_argument("--tags", nargs="*", default=[])

    jobs = sub.add_parser("jobs", help="List ingestion jobs for a tenant.")
    jobs.add_argument("--tenant-id", type=_parse_uuid, required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    headers = {"Authorization": f"Bearer {args.api_token}"}

    with httpx.Client(base_url=args.base_url, timeout=15.0) as client:
        if args.command == "upload":
            file_bytes = args.file.read_bytes()
            files = {
                "file": (args.file.name, file_bytes, "application/octet-stream"),
            }
            data = {
                "tenant_id": str(args.tenant_id),
                "brand_id": str(args.brand_id),
                "visibility": args.visibility,
                "tags": json.dumps(args.tags),
            }
            response = client.post(
                "/admin/knowledge_assets/upload",
                headers=headers,
                files=files,
                data=data,
            )
            response.raise_for_status()
            body = response.json()
            print("✅ Uploaded asset:", json.dumps(body, indent=2))
        elif args.command == "jobs":
            response = client.get(
                "/admin/ingestion_jobs",
                headers=headers,
                params={"tenant_id": str(args.tenant_id)},
            )
            response.raise_for_status()
            jobs = response.json()
            print(json.dumps(jobs, indent=2))

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
