#!/usr/bin/env python3
"""Restore Xin ChatBot data from S3/offline archives."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
from typing import Dict


def parse_env_file(path: pathlib.Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in path.read_text().splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def download_archive(bucket: str, timestamp: str, destination_dir: pathlib.Path) -> pathlib.Path:
    archive = destination_dir / f"xin-backup-{timestamp}.tar.gz"
    cmd = ["aws", "s3", "cp", f"s3://{bucket}/xin-backup-{timestamp}.tar.gz", str(archive)]
    subprocess.run(cmd, check=True)
    return archive


def restore_postgres(backup_dir: pathlib.Path, env: Dict[str, str]) -> None:
    dump_file = backup_dir / "postgres.dump"
    if not dump_file.exists():
        raise FileNotFoundError("postgres.dump missing in archive")
    pg_env = os.environ.copy()
    pg_env["PGPASSWORD"] = env.get("POSTGRES_PASSWORD", "")
    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "-h",
        env.get("POSTGRES_HOST", "localhost"),
        "-p",
        env.get("POSTGRES_PORT", "5432"),
        "-U",
        env.get("POSTGRES_USER", "chatbot"),
        "-d",
        env.get("POSTGRES_DB", "chatbot"),
        str(dump_file),
    ]
    subprocess.run(cmd, check=True, env=pg_env)


def restore_qdrant(backup_dir: pathlib.Path, env: Dict[str, str]) -> None:
    snapshot = next(backup_dir.glob("qdrant-*.snap"), None)
    if snapshot is None:
        print(":: Qdrant snapshot not found, skipping restore")
        return
    url = env.get("QDRANT_URL", "http://localhost:6333").rstrip("/")
    cmd = [
        "curl",
        "-fsS",
        "-X",
        "POST",
        f"{url}/snapshots/upload",
        "-F",
        f"snapshot=@{snapshot}",
    ]
    if env.get("QDRANT_API_KEY"):
        cmd.extend(["-H", f"api-key: {env['QDRANT_API_KEY']}"])
    subprocess.run(cmd, check=True)


def restore_object_storage(backup_dir: pathlib.Path, env: Dict[str, str]) -> None:
    folder = backup_dir / "object-storage"
    if not folder.exists():
        print(":: Object storage export missing, skipping")
        return
    bucket = env.get("STORAGE_BUCKET")
    if not bucket:
        print(":: STORAGE_BUCKET not configured; cannot restore object storage")
        return
    endpoint = env.get("STORAGE_ENDPOINT_URL", "https://s3.amazonaws.com")
    cmd = [
        "aws",
        "--endpoint-url",
        endpoint,
        "s3",
        "sync",
        str(folder),
        f"s3://{bucket}",
        "--delete",
    ]
    subprocess.run(cmd, check=True)


def extract_archive(archive: pathlib.Path, tmpdir: pathlib.Path) -> pathlib.Path:
    with tarfile.open(archive) as tar:
        tar.extractall(tmpdir)
    # archive root is timestamp directory
    contents = [p for p in tmpdir.iterdir() if p.is_dir()]
    if not contents:
        raise RuntimeError("Archive did not contain a backup directory")
    return contents[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore Xin backups")
    parser.add_argument("--env-file", default="deploy/compose/.env.dev", help="dotenv with DB/storage secrets")
    parser.add_argument("--archive", help="Path to backup archive (.tar.gz)")
    parser.add_argument("--timestamp", help="Timestamp used in backup archive filename")
    parser.add_argument("--bucket", default="xin-db-backups", help="S3 bucket containing backups")
    args = parser.parse_args()

    env_path = pathlib.Path(args.env_file).expanduser()
    if not env_path.exists():
        raise FileNotFoundError(env_path)
    env = parse_env_file(env_path)

    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="xin-restore-"))
    try:
        archive_path: pathlib.Path
        if args.archive:
            archive_path = pathlib.Path(args.archive).expanduser()
        elif args.timestamp:
            archive_path = download_archive(args.bucket, args.timestamp, tmpdir)
        else:
            raise SystemExit("Either --archive or --timestamp is required")

        if not archive_path.exists():
            raise FileNotFoundError(archive_path)

        print(f":: Extracting {archive_path}")
        backup_dir = extract_archive(archive_path, tmpdir)
        print(":: Restoring Postgres")
        restore_postgres(backup_dir, env)
        print(":: Restoring Qdrant")
        restore_qdrant(backup_dir, env)
        print(":: Restoring object storage")
        restore_object_storage(backup_dir, env)
        print(":: Restore complete")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
