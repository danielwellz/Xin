# Xin ChatBot Architecture

## 1. System Overview
Xin ChatBot is composed of a stateless API surface backed by a streaming orchestrator, channel adapters, a retrieval-augmented generation (RAG) pipeline, and background workers for ingestion plus automation. The system is deployed as a set of containers or services communicating over an internal event bus (Redis/Kafka) and persisting canonical state in Postgres and Qdrant.

```
Clients → Channel Gateway → Orchestrator API → Policy Engine → LLM + RAG → Response
                                     ↘ Automation Workers ↙
                                     ↘ Analytics + Alerts ↙
```

## 2. Core Services
| Service | Responsibilities | Tech Highlights |
| --- | --- | --- |
| `xin_orchestrator` | HTTP + gRPC entry point, tenant-aware routing, policy evaluation | FastAPI, Pydantic, JWT auth |
| `xin_channel_gateway` | Normalizes inbound events from Instagram, Telegram, WhatsApp, Web widget | Asyncio workers, signed webhooks |
| `xin_rag_worker` | Chunking, embedding, storage, retrieval scoring | Sentence Transformers/OpenAI, Qdrant |
| `xin_ingestion_worker` | File ingestion queue, OCR, metadata extraction | Celery + Redis |
| `xin_automation_worker` | Schedules follow-ups, escalations, CRM pushes | APScheduler |
| `xin_frontend` | Operator console + embed widget (React, optional) | Vite + Tailwind |

## 3. Data Flow
1. **Inbound Event**: Channels POST to `/webhooks/<channel>` on the gateway.
2. **Normalization**: Gateway converts payloads into `ChatEvent` dataclasses and publishes to Redis streams.
3. **Orchestration**: API layer consumes events, loads tenant + channel config, and invokes the policy engine.
4. **Knowledge Retrieval**: Policy engine queries Qdrant using embeddings pulled from ingestion jobs.
5. **Response Generation**: LLM provider (OpenAI or local) is prompted with retrieved context plus policies.
6. **Dispatch**: Generated reply is pushed back through the gateway to the originating channel; transcripts are
   persisted in Postgres with a vector copy in Qdrant for analytics.

## 4. Storage & Configuration
- **Postgres** — tenants, channels, conversation transcripts, automation states.
- **Qdrant** — vector store keyed by tenant, supports hybrid BM25 + dense retrieval.
- **Redis** — rate limiting, stream bus, cache of tenant feature flags.
- **Object Storage (S3/MinIO)** — uploaded documents, media, and backups.
- **Secrets** — stored in `.env` per environment; production uses Vault-compatible secret mounts.

## 5. Security & Compliance
- JWT-based admin API; per-tenant HMAC secrets for channel callbacks.
- Pydantic validation for all inbound payloads, with redaction of PII in logs.
- Audit log appended for every policy or automation change.
- Network segmentation: public channels → gateway → private orchestrator subnet.

## 6. Deployment Topology
- **Local Dev**: Docker Compose, single-instance services sharing a dev Postgres and Qdrant.
- **Staging**: Kubernetes namespace with horizontal pod autoscaling on orchestrator + gateway.
- **Prod**: Multi-region active/standby; Postgres HA pair, Qdrant replicated, workers sharded by tenant.

## 7. Observability
- OpenTelemetry traces exported to Tempo.
- Structured JSON logs with `tenant_id` and `channel_id` tags.
- Prometheus metrics for request rate, latency, queue depth, ingestion lag, LLM token usage.
- Grafana dashboards: API health, ingestion health, automation SLAs.

## 8. Extensibility Notes
- Add new channels by implementing `ChannelAdapter` under `src/chatbot/adapters/`.
- Policy engine accepts plug-in evaluators (Python entry points) for custom tenant rules.
- Retrieval pipeline can swap embeddings via `EmbeddingSettings` without reworking ingestion logic.
- Frontend embed widget consumes `/embed.js?tenant_id=…` exposing minimal public surface.

## 9. Outstanding Gaps
- Web widget auto-config generator still pending; currently manual snippet assembly.
- Systemd + SSL automation (Certbot/ACME) needed for bare-metal installs.
- Monitoring dashboard requires runbooks aligned with SLOs defined below.
- Delivery coordination captured in `docs/delivery/integrated_plan.md`; keep it in sync with architecture deltas when closing each phase.
