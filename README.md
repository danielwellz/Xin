# Xin ChatBot

Xin is a multi-tenant, multi-channel messaging platform that ingests tenant
knowledge, runs RAG + policy evaluation, and responds to customers on Instagram,
WhatsApp Business, Telegram, and the hosted web widget.

## Services & directories

| Component | Location | Notes |
| --- | --- | --- |
| Orchestrator API | `src/chatbot/apps/orchestrator` | FastAPI app (`uvicorn chatbot.apps.orchestrator.app:create_app`) |
| Channel Gateway | `src/chatbot/apps/gateway` | FastAPI webhooks + outbound worker |
| Ingestion worker | `src/chatbot/apps/ingestion` | ARQ worker + document pipeline |
| Automation worker | `src/chatbot/automation` | APScheduler loop (shares orchestrator image) |
| React operator console | `services/frontend` | Tenant/channel/policy UI |
| Widget SDK | `services/widget` | `/embed.js` bundle + React bindings |

See `docs/ARCHITECTURE.md` for the Phase 3 snapshot and the target `chatbot.apps.*`
layout introduced in this refactor.

---

## Local development

### Backend via Poetry

1. Install deps and copy the developer env template:

   ```bash
   poetry install
   cp .env.example .env.local
   ```

2. Start the stateful services (Postgres, Redis, Qdrant, MinIO) via Docker:

   ```bash
   docker compose up -d postgres redis qdrant minio
   ```

3. Run the orchestrator with hot reload:

   ```bash
   poetry run uvicorn chatbot.apps.orchestrator.app:create_app --factory --reload
   ```

4. Optional helpers:

   ```bash
   # Gateway webhooks for local testing
   poetry run uvicorn chatbot.apps.gateway.app:create_app --factory --port 8080

   # Ingestion worker
   poetry run arq chatbot.apps.ingestion.worker.WorkerSettings
   ```

5. CLI smoke test:

   ```bash
   poetry run python -m chatbot.cli \
     --host http://localhost:8000 \
     --tenant-id <tenant_uuid> \
     --brand-id <brand_uuid> \
     --channel-id <channel_uuid>
   ```

6. Upload a knowledge doc:

   ```bash
   curl -F "file=@docs/faq.md" \
     http://localhost:8000/v1/brands/<brand_uuid>/knowledge
   ```

### Local prod-like stack (Docker Compose)

1. Copy the Compose template and tweak any secrets:

   ```bash
   cp config/examples/.env.docker.example config/.env.docker
   ```

2. Bring the stack online (defaults to `config/.env.docker`). Set
   `XIN_ENV_FILE` if you keep the env file elsewhere.

   ```bash
   docker compose --env-file config/.env.docker up -d
   docker compose --env-file config/.env.docker ps
   ```

3. Tear down with `docker compose down` when finished. Named volumes persist
   Postgres/Qdrant/Redis data between runs.

### Operator console

1. `cd services/frontend && pnpm install`
2. Copy `.env.example` → `.env` if you need to override `VITE_API_BASE_URL`
   (defaults to `window.location.origin` so xinbot.ir works without extra config).
3. `pnpm dev` for local development (`VITE_USE_MOCKS=true` boots MSW fixtures).
4. `pnpm e2e` to run the Cypress smoke suite, `pnpm lint` / `pnpm test` for
   static checks.
5. Production builds use the Dockerfile in `services/frontend`. After updating
   the console run `docker compose --env-file <envfile> build frontend && docker compose --env-file <envfile> up -d frontend`, reload Nginx, and purge the ArvanCloud cache.

---

## Deployment

`DEPLOYMENT.md` documents the full Debian 12 deploy plan (user creation, Docker,
Nginx + Let’s Encrypt, env files, ArvanCloud notes, and redeploy commands). The
legacy Phase 3 runbook is preserved under `docs/deployment/xinbot_final_runbook.md`
for historical reference.

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
for contribution history. For live ops run through `DEPLOYMENT.md`.
