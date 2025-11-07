# Codex Prompt Stack — Enterprise Messaging Assistant

Use this prompt sequence to guide Codex through building a production-grade, Python-based multi-channel business assistant. Submit each prompt in order, confirm success (tests, lint, migrations) before advancing, and adapt only environment-specific values (e.g., ports, domains).

---

## 0. Foundation Guardrails
> Before we begin, audit the repository. Remove any temporary artifacts, ensure `.gitignore` covers virtualenvs, `.pytest_cache`, and compiled assets, and set the project default to Python 3.11.

---

## 1. Workspace Bootstrap
> Initialize a Poetry-driven monorepo with packages:
> - `services/orchestrator`
> - `services/ingestion_worker`
> - `services/channel_gateway`
> - `packages/core`
> - `packages/rag`
> Configure a root `pyproject.toml` using Poetry 1.7+, enable namespace packages, set `tool.poetry.group.dev` for shared dependencies (ruff, black, pytest, mypy, coverage). Scaffold a `Makefile` exposing `make setup`, `make lint`, `make test`, and `make format`. Add `.env.example` capturing shared environment variables.

---

## 2. Architecture Blueprint Documentation
> Create `docs/ARCHITECTURE.md` describing the system context: channel adapters, orchestrator, ingestion pipeline, vector store, and LLM provider. Include component diagrams (Mermaid) and data flow notes (request lifecycle, knowledge ingestion path, escalation loop).

---

## 3. Core Package & Design System
> In `packages/core`, implement:
> - Config loader (`pydantic-settings`) with structured settings classes for Postgres, Redis, Qdrant, OpenAI/OpenRouter.
> - Logging module using `structlog` with OpenTelemetry enrichment.
> - Domain models (`dataclasses`) for `Tenant`, `BrandProfile`, `Channel`, `InboundMessage`, `OutboundResponse`, `KnowledgeAsset`, and `ActionRequest`.
> - Common HTTP/error types, response schemas (FastAPI-compatible), and utilities for tracing IDs and retry helpers.
> Provide unit tests ensuring settings precedence (env vars vs .env) and logging context injection.

---

## 4. Retrieval & Knowledge Package
> Port Hooshpod RAG logic into `packages/rag` with the following modules:
> - `chunking.py` supporting semantic-aware splitting (markdown, FAQ tables) with configurable overlap.
> - `embeddings.py` supporting OpenAI `text-embedding-3-large` and offline `sentence-transformers` fallback.
> - `vector_store.py` integrating with Qdrant (HTTP) and an in-memory stub for tests, namespaced per tenant/brand.
> - `retrieval.py` exporting `initialize_brand_knowledge`, `refresh_brand_knowledge`, and `retrieve_context`.
> Include pytest coverage for chunking edge cases and retrieval scoring. Ensure embeddings layer exposes async and sync interfaces.

---

## 5. Persistence & Schema Governance
> Inside `packages/core/db`, configure SQLModel (or SQLAlchemy 2.0 declarative) models and Alembic migrations. Model `Tenant`, `Brand`, `ChannelConfig`, `PersonaProfile`, `Conversation`, `MessageLog`, `KnowledgeSource`, `KnowledgeChunk`, and `AutomationRule`. Set up a shared migration environment with `alembic.ini` at repo root and scripts for `alembic revision --autogenerate`.

---

## 6. Orchestrator Service (FastAPI)
> Scaffold `services/orchestrator` with FastAPI. Implement endpoints:
> - `POST /v1/messages/inbound`: validate `InboundMessage`, upsert conversation state, retrieve RAG context, craft persona-aware prompt, call LLM (OpenAI-compatible), run guardrails (safe completion checks, escalation routing), log to Postgres, publish outbound payload to Redis stream.
> - `POST /v1/brands/{brand_id}/knowledge`: accept document uploads (text, markdown, PDF via textract), enqueue ingestion jobs.
> - `GET /v1/conversations/{conversation_id}`: return history with context snippets.
> Use dependency-injected services, ensure transactional integrity, and add pytest integration tests with test containers (Postgres, Redis, Qdrant).

---

## 7. Ingestion Worker (Async Worker)
> Build `services/ingestion_worker` using `arq` or `rq` with asyncio support. The worker should:
> - Consume `KnowledgeIngestJob`s from Redis.
> - Fetch source documents (S3-compatible MinIO for dev), normalize, chunk, embed, and store vectors in Qdrant under tenant/brand collections.
> - Update ingestion status in Postgres and emit progress over Redis Pub/Sub.
> Add resilience (retry with exponential backoff, poison queue handling) and unit tests for ingestion pipeline stages.

---

## 8. Channel Gateway
> Implement `services/channel_gateway` with separate routers for Instagram, WhatsApp, Telegram, and Web chat:
> - Expose webhook endpoints validating provider signatures.
> - Map provider payloads to `InboundMessage`.
> - Forward to orchestrator via REST/async queue.
> - Consume outbound messages from Redis stream and call provider SDKs (wrap in adapter classes; mock in tests).
> Provide a local simulator for callbacks and record fixtures for contract tests.

---

## 9. Conversational Guardrails & Action Framework
> Extend the orchestrator to support action plans:
> - Implement a rule engine that inspects LLM outputs for `ActionRequest` blocks (JSON schema).
> - Create plugins for order lookup, ticket creation, FAQ fallback. Stub integrations with pluggable registry.
> - Add safety filters (profanity, PII leakage) using `guardrails-ai` or self-hosted policies.

---

## 10. Observability, Testing, and Performance
> Configure:
> - Distributed tracing with OpenTelemetry (OTLP exporter), metrics via Prometheus client.
> - Structured request/response logging with correlation IDs.
> - pytest suites (unit, integration, contract), coverage thresholds ≥85%.
> - Load tests using Locust targeting 50 concurrent conversations per brand.
> Update `Makefile` to run lint, type-check, tests, and load tests. Document troubleshooting in `docs/RUNBOOK.md`.

---

## 11. Delivery & Deployment
> Dockerize each service (multi-stage builds), align images via docker-compose for local dev, and add Kubernetes manifests (Helm chart) for staging/prod. Configure GitHub Actions to run CI (lint, type check, test, build, scan) and CD (push images, deploy via helm). Document secret management with Doppler/Vault and provide post-deploy smoke test script.

---

## 12. Final Review
> Run the full `make test` and `make lint` suite, confirm coverage, validate migrations, and summarize the system in `docs/RELEASE_NOTES.md`. Request Codex to highlight remaining risks and suggested next iterations.
