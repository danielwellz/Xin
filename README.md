# Business Messaging Platform

Xin is a multi-channel, multi-tenant messaging assistant that blends knowledge
ingestion, RAG retrieval, and automated responses. The repository hosts three
services:

- **Orchestrator** – FastAPI API that processes inbound messages, persists
  conversation state, calls the LLM, and emits outbound responses.
- **Channel Gateway** – Webhook façade for channel providers (Instagram,
  WhatsApp, Telegram, Web Chat) that forwards normalized payloads to the
  orchestrator and delivers outbound responses.
- **Ingestion Worker** – Asynchronous worker that ingests knowledge uploads into
  MinIO/S3, chunks content, generates embeddings, and upserts vectors to Qdrant.
- **Widget SDK** – Lightweight embed (`services/widget`) that exposes `/embed.js` and React bindings for client-facing chat.
- **Frontend** – Vite + React operator console (Phase 3 parity) located at
  `services/frontend` with bilingual tenant/channel/policy tooling.

## Quick Start

1. **Install dependencies**

   ```bash
   poetry install
   ```

2. **Start infrastructure**

   ```bash
   docker compose up postgres redis qdrant minio -d
   ```

3. **Configure environment**

   Copy `.env.example` (or create `.env`) and provide values for:

   - `POSTGRES_*`, `REDIS_URL`, `QDRANT_*`
   - `STORAGE_ENDPOINT_URL`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`,
     `STORAGE_BUCKET`
   - `INGEST_REDIS_HOST`, `INGEST_REDIS_PORT`, `INGEST_REDIS_DB`,
     `INGEST_QUEUE_NAME`

4. **Run the orchestrator**

   ```bash
   poetry run uvicorn chatbot.adapters.orchestrator.app:create_app \
     --factory --host 0.0.0.0 --port 8000
   ```

5. **Simulate a chat session**

   ```bash
   poetry run python -m chatbot.cli \
     --host http://localhost:8000 \
     --tenant-id <tenant_uuid> \
     --brand-id <brand_uuid> \
     --channel-id <channel_uuid>
   ```

   The CLI opens an interactive prompt that posts `POST /v1/messages/inbound`
   calls and prints the orchestrator's response payload.

6. **Upload knowledge**

   ```bash
   curl -F "file=@docs/faq.md" \
     http://localhost:8000/v1/brands/<brand_uuid>/knowledge
   ```

   The orchestrator stores the file in object storage and enqueues an ingestion
   job. Ensure the ingestion worker is running:

   ```bash
   poetry run arq chatbot.adapters.ingestion.worker.WorkerSettings
   ```

### Operator Console (Phase 3)

1. `cd services/frontend && pnpm install`
2. Copy `.env.example` → `.env` if you need to override `VITE_API_BASE_URL`. (Production
   defaults to `window.location.origin`, so xinbot.ir works without extra config.)
3. `pnpm dev` to run against the orchestrator (`VITE_USE_MOCKS=true` boots MSW data).
4. Run the Cypress smoke tests in both locales with `pnpm e2e`.
5. See `services/frontend/README.md` and `docs/frontend/operator_console.md` for screenshots, tooling, and deployment notes.
6. Production deploys keep the `frontend` container online and serve it at `/` via Nginx (`/api` continues to hit the FastAPI orchestrator, `/webhooks` routes to the channel gateway). After any release run
   `docker compose --env-file ../config/compose.env build frontend && docker compose --env-file ../config/compose.env up -d frontend`, reload Nginx, and purge the CDN cache so `https://xinbot.ir` renders the
   React console immediately.

## Development Commands

- `make format` – Run `black` + `ruff --fix`.
- `make test` – Execute the entire pytest suite.
- `make test-integration` – Run the integration suite (requires Docker).
- `make verify` – Lint, type-check, and ensure coverage ≥ 85%.
- `make ci` – Aggregates backend + frontend/widget checks (mirrors `.github/workflows/ci.yml`).
- `make demo ADMIN_TOKEN=<platform_admin_jwt>` – Spins up the demo stack and seeds a tenant/channel for recordings.

### Admin token bootstrap

Both the operator console and helpers like `make demo` need a `platform_admin` JWT. Use the existing JWT service (`src/chatbot/admin/auth.py`) plus settings (`src/chatbot/core/config.py`) to mint one on the host:

```bash
cd /opt/xin-chatbot/src
poetry run python - <<'PY'
from chatbot.admin.auth import JWTService
from chatbot.core.config import AppSettings
settings = AppSettings.load()
svc = JWTService(
    secret=settings.admin_auth.jwt_secret,
    issuer=settings.admin_auth.issuer,
    audience=settings.admin_auth.audience,
    ttl_seconds=settings.admin_auth.access_token_ttl_minutes * 60,
)
print(svc.issue_token(subject="bootstrap-ops", roles=["platform_admin"]))
PY
```

Paste the printed token into the console login modal and export it for CLI helpers (`export ADMIN_TOKEN=<jwt>`).

See `AGENTS.md`, `docs/RUNBOOK.md`, and `docs/deployment/xinbot_final_runbook.md`
for detailed contribution, operations, and production deployment guidance.
