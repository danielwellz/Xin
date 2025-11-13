#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-./deploy/compose/.env.dev}"
BACKUP_BUCKET="${BACKUP_BUCKET:-xin-db-backups}"
WORKDIR="${WORKDIR:-/tmp/xin-backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE_NAME="xin-backup-${TIMESTAMP}.tar.gz"

usage() {
  echo "Usage: ENV_FILE=path BACKUP_BUCKET=name $0" >&2
}

if [[ ! -f "$ENV_FILE" ]]; then
  usage
  exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

mkdir -p "$WORKDIR/$TIMESTAMP"
PERSIST_DIR="$WORKDIR/$TIMESTAMP"

echo ":: Dumping Postgres"
export PGPASSWORD="${POSTGRES_PASSWORD:-${POSTGRES_PASS:-}}"
pg_dump -Fc \
  -h "${POSTGRES_HOST:-localhost}" \
  -p "${POSTGRES_PORT:-5432}" \
  -U "${POSTGRES_USER:-chatbot}" \
  "${POSTGRES_DB:-chatbot}" > "$PERSIST_DIR/postgres.dump"

if [[ -n "${QDRANT_URL:-}" ]]; then
  echo ":: Creating Qdrant snapshot"
  AUTH_HEADER=()
  if [[ -n "${QDRANT_API_KEY:-}" ]]; then
    AUTH_HEADER=(-H "api-key: $QDRANT_API_KEY")
  fi
  SNAPSHOT_NAME="$(curl -fsS -X POST "${QDRANT_URL%/}/snapshots" "${AUTH_HEADER[@]}" | python - <<'PY'
import json, sys
payload = json.load(sys.stdin)
print(payload["result"]["name"])
PY
)"
  curl -fsS "${QDRANT_URL%/}/snapshots/${SNAPSHOT_NAME}" "${AUTH_HEADER[@]}" \
    -o "$PERSIST_DIR/qdrant-${SNAPSHOT_NAME}.snap"
fi

if [[ -n "${STORAGE_BUCKET:-}" ]]; then
  echo ":: Syncing object storage bucket ${STORAGE_BUCKET}"
  aws --endpoint-url "${STORAGE_ENDPOINT_URL:-https://s3.amazonaws.com}" \
    s3 sync "s3://${STORAGE_BUCKET}" "$PERSIST_DIR/object-storage"
fi

echo ":: Creating archive"
tar -C "$WORKDIR" -czf "$WORKDIR/$ARCHIVE_NAME" "$TIMESTAMP"

if [[ -n "$BACKUP_BUCKET" ]]; then
  echo ":: Uploading archive to s3://${BACKUP_BUCKET}/${ARCHIVE_NAME}"
  aws s3 cp "$WORKDIR/$ARCHIVE_NAME" "s3://${BACKUP_BUCKET}/${ARCHIVE_NAME}"
fi

echo ":: Backup ready at $WORKDIR/$ARCHIVE_NAME"
