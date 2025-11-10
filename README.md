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

## Development Commands

- `make format` – Run `black` + `ruff --fix`.
- `make test` – Execute the entire pytest suite.
- `make test-integration` – Run the integration suite (requires Docker).
- `make verify` – Lint, type-check, and ensure coverage ≥ 85%.

See `AGENTS.md` and `docs/RUNBOOK.md` for detailed contribution and operations
guidelines.
