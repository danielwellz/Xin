# Xin ChatBot Architecture

This document captures both the **current Phase 3 architecture** (pre-refactor snapshot) and the **target Phase 4 design** that the repository is being refactored toward. The goal is to keep contributors aligned while we reorganise the services, enforce stricter multi-tenancy controls, and ship a production-ready deploy story for xinbot.ir.

---

## 1. Current System Snapshot (Phase 3)

> **Note:** Paths in this section reference the pre-refactor (`chatbot.adapters.*`)
> layout. They are retained for posterity so release notes and prior docs remain
> meaningful. See §2 for the new `chatbot.apps.*` module structure.

### 1.1 Services, stacks, and code locations

| Component | Responsibilities | Stack | Code entry point(s) |
| --- | --- | --- | --- |
| Orchestrator API | FastAPI service that exposes `/v1` APIs, admin endpoints, retrieves knowledge, calls the LLM, and emits outbound payloads to Redis streams. Handles JWT auth for the operator console. | Python 3.11, FastAPI, SQLModel, Redis, OpenTelemetry | `src/chatbot/adapters/orchestrator/app.py`, packaged via `services/orchestrator/Dockerfile`. |
| Channel Gateway | FastAPI façade that receives Instagram / WhatsApp / Telegram / Web widget callbacks, normalises payloads, and forwards them to the orchestrator. A companion worker consumes Redis streams to deliver outbound replies. | Python 3.11, FastAPI, redis-py | `src/chatbot/adapters/channel_gateway/app.py` and `worker.py`, containerised under `services/channel_gateway`. |
| Ingestion Worker | ARQ worker that fetches uploaded docs from MinIO/S3, chunks markdown, embeds text, and upserts vectors into Qdrant. | Python 3.11, ARQ, Redis, aioboto3, Qdrant HTTP | `src/chatbot/adapters/ingestion/worker.py`, `services/ingestion_worker/Dockerfile`. |
| Automation Worker | APScheduler loop that reads automation rules/jobs out of Postgres, evaluates policy guardrails, and fires connectors. | Python 3.11, APScheduler | `src/chatbot/automation/worker.py`, shares the orchestrator base image. |
| Operator Console | React + Vite application for tenants, channels, knowledge, policies, automations, and observability. | Typescript, React Query, Tailwind, Cypress | `services/frontend` (Dockerised to Nginx) |
| Widget SDK | Lightweight embed + React bindings for the hosted web chat. | Typescript, Vite | `services/widget` |

### 1.2 Message lifecycle (user → AI → channel)

```
Channel provider → FastAPI gateway (/webhooks/<channel>) → orchestrator POST /v1/messages/inbound
  → policy engine (`src/chatbot/policy/engine.py`) decides guardrails/retrieval config
  → context service pulls embeddings via `chatbot.rag` + Qdrant
  → `LLMClient` assembles persona prompt + history + knowledge and synthesises reply
  → outbound log persisted in Postgres (`chatbot.core.db.models`)
  → Redis stream `outbound:messages`
  → gateway outbound worker dispatches to provider adapters (Instagram/WhatsApp/Telegram/Web)
```

### 1.3 Data persistence & multi-tenancy

- **Postgres (SQLModel models in `chatbot.core.db.models`)** stores tenants, brands, channels, secrets, personas, knowledge assets, ingestion jobs, conversations, message logs, and automation rules. Every table carries `tenant_id` and/or `brand_id` for soft isolation.
- **Redis** fulfils two roles: (1) orchestrator writes outbound payloads to the `outbound:messages` stream, and (2) ARQ/automation leverage Redis for queues + progress channels.
- **Qdrant** hosts tenant-scoped vector collections referenced via `chatbot.rag.vector_store.QdrantVectorStore`.
- **Object storage (MinIO/S3)** stores raw knowledge uploads. `chatbot.core.storage.ObjectStorageClient` interacts with it, while ingestion pulls the data back for embedding.
- **Configuration** comes from `.env` (loaded by `chatbot.core.config.AppSettings` with nested settings for Postgres, Redis, Qdrant, storage, LLM, etc.). Additional `.env` templates live under `deploy/compose/.env.dev.example` and service directories (e.g., `services/frontend/.env.example`).

### 1.4 Integration points

- **Instagram / WhatsApp / Telegram** webhooks hit FastAPI routers in `src/chatbot/adapters/channel_gateway/routers`. Secrets are validated (e.g., HMAC for Instagram) before messages are forwarded to the orchestrator via `OrchestratorClient`.
- **Web chat widget** posts to the `/web` router, sharing the same normalization path.
- **Knowledge ingestion** uses the admin API: file uploads land in MinIO through `KnowledgeService`, then ARQ jobs enqueue via `IngestionJobPublisher`.
- **LLM + embeddings** currently call OpenAI synchronously; fallback to Sentence Transformers exists for offline dev.
- **Automation connectors** (placeholder) live inside `src/chatbot/automation/connectors.py`, triggered by APScheduler.
- **Frontend ↔ orchestrator** communicates through `/admin/*` endpoints with JWT auth minted by `chatbot.admin.auth.JWTService`.

### 1.5 Deployment baseline

- `docker-compose.yml` spins up Postgres, Redis, Qdrant, MinIO, orchestrator, channel gateway, ingestion worker, automation worker, frontend, and an optional Caddy-based edge proxy.
- Production runbook (`docs/deployment/xinbot_final_runbook.md`) assumes Ubuntu 24.04, Docker Compose, Nginx proxying `/`, `/api/`, and `/webhooks/`, with TLS handled by certbot and ArvanCloud sitting in front.
- SystemD units in `deploy/systemd/` know how to run `uvicorn chatbot.apps.orchestrator.app:create_app` etc.

---

## 2. Target Phase 4 Architecture

### 2.1 Principles

1. **Explicit service boundaries** under `src/chatbot/apps/` so each surface owns its FastAPI/worker wiring while sharing domain modules under `chatbot.core`, `chatbot.policy`, `chatbot.rag`, etc.
2. **Strict multi-tenancy** with consistent `tenant_id` propagation, policy enforcement prior to LLM calls, and scoped storage namespaces.
3. **Three-tier environment strategy** with dedicated env files: `.env.local` (developer laptop), `.env.docker` (local prod-like), `.env.production` (VPS).
4. **Single source of truth for deployment** so docker compose, Nginx, and env files line up for local dev and xinbot.ir (Debian 12 + Nginx + Docker Compose + ArvanCloud).

### 2.2 Module layout

```
src/chatbot/
  apps/
    orchestrator/        # FastAPI app, routers, dependencies, services wrapper
    gateway/             # FastAPI webhooks + outbound worker
    ingestion_worker/    # ARQ worker + pipeline adapters
    automation_worker/   # APScheduler runner
  core/                  # config, db, domain, middleware, storage, logging
  admin/ / automation/ / rag/ / policy/ ... (domain + shared logic)
```

All service entry points import from `chatbot.apps.<service>` rather than `chatbot.adapters.*`. Dockerfiles, CLI helpers, and docs will reference the new module path.

### 2.3 Data & control flow (target)

1. **Inbound** traffic hits `gateway` (FastAPI) which authenticates channel secrets, maps provider payloads to `InboundMessage`, and forwards via `OrchestratorClient`.
2. **Orchestrator** performs:
   - Idempotent conversation upsert, message logging, persona lookup.
   - Policy evaluation (`PolicyEngine`) to determine retrieval rules and guardrails.
   - Context retrieval via `ContextService` (OpenAI embeddings + Qdrant).
   - Prompt construction + LLM call via the upgraded `LLMClient` (supports provider overrides per tenant).
   - Guardrail validation and outbound logging, writing final payload to Redis streams.
3. **Outbound worker** (gateway) consumes Redis `outbound:messages` with consumer groups; provider adapters per channel deliver messages downstream.
4. **Knowledge uploads**: Admin API pushes files to object storage; registration writes `KnowledgeAsset` + `IngestionJob`. `IngestionJobPublisher` uses ARQ to enqueue jobs, the ingestion worker fetches/chunks/embeds, and Qdrant becomes query-ready.
5. **Automation**: APScheduler polls active rules, ensures policy pass, and calls connectors (future-proofed for CRM hooks).

### 2.4 Environment layers

| File | Purpose | Loading order |
| --- | --- | --- |
| `.env.local` | Developer defaults (SQLite override optional) for running services via Poetry/PNPM without Docker. | Auto-loaded by `BaseAppSettings` (python-dotenv). |
| `.env.docker` | Compose defaults for local prod-like stack (`docker compose --env-file config/.env.docker up`). Lives under `config/`. | Passed explicitly to `docker compose` and services. |
| `.env.production` | Secret-rich configuration for xinbot.ir stored at `/opt/xin-chatbot/config/.env.production` (never committed). | Referenced from deploy instructions + systemd unit. |

All env templates document variables grouped by concern (database, cache, vector store, storage, LLM, channels, telemetry).

### 2.5 Deployment topology

- **Docker Compose (local + prod)** orchestrates Postgres, Redis, Qdrant, MinIO, orchestrator, gateway, ingestion worker, automation worker, frontend, widget bundle, and Nginx edge proxy (prod only). Named volumes handle persistent data.
- **Nginx on Debian 12** proxies:
  - `/` → frontend container (`xin_frontend`)
  - `/api/` → orchestrator (`xin_orchestrator`)
  - `/webhooks/` → gateway (`xin_gateway`)
  - Static `/embed.js` served by widget container or orchestrator static endpoint.
- **ArvanCloud** sits in front with HTTPS; Nginx config disables caching for `/api/` and `/webhooks/` to keep webhook delivery deterministic.

### 2.6 Observability

- Unified OTLP exporter settings per service with labels `service_name=xin-<component>`.
- `/metrics` endpoints on API services, `prometheus_client` exporters on workers (ingestion + automation).
- Correlation IDs from `RequestContextMiddleware` propagate through orchestrator + gateway; outbound worker adds trace metadata to Redis payloads.

### 2.7 Open tasks captured by the refactor

- Move FastAPI/worker apps under `chatbot.apps.*` and update Docker/systemd/docs accordingly.
- Normalize environment files & secrets.
- Provide reproducible deployment instructions for Debian 12 + Docker Compose + Nginx + certbot + ArvanCloud caching guidance.
- Ensure README, DEPLOYMENT guide, and docs reference the new architecture and workflows.

---

Keep this document current whenever service boundaries or deployment processes change. Contributors should reference §1 to understand legacy behaviours and §2 to see the intended steady state.
