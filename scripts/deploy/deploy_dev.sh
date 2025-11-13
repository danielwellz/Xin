#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/deploy/compose/.env.dev}"
COMPOSE_FILES=(-f "$ROOT_DIR/docker-compose.yml" -f "$ROOT_DIR/deploy/observability/docker-compose.yml")

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/deploy/compose/.env.dev.example" "$ENV_FILE"
  echo ":: Created $ENV_FILE from example template. Update secrets before continuing."
fi

echo ":: Pulling latest images"
docker compose --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" pull

echo ":: Building/updating services"
docker compose --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" up -d --build --remove-orphans

echo ":: Applying database migrations"
docker compose --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" run --rm orchestrator alembic upgrade head

echo ":: Waiting for edge proxy health"
bash "$ROOT_DIR/scripts/systemd/healthcheck.sh" --url "https://localhost:8443/health" --insecure --max-wait 120 --name "compose edge proxy"

docker compose --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" ps
