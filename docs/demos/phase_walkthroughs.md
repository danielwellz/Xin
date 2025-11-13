# Phase Demo Scripts

Each phase has a reproducible script, data prerequisites, and a placeholder for the latest recording. Run `make demo` to seed the environment, then follow the steps below. Store recordings in the shared drive and update the links after every acceptance review.

## Phase 1 — Admin Core

- **API Flow**
  1. `make demo ADMIN_TOKEN=<platform_admin_jwt>` (provisions tenant + channel).
  2. Show `POST /admin/tenants` + `POST /admin/channels` responses in HTTPie.
  3. Fetch audit log via `GET /admin/audit?tenant_id=<id>`.
- **Acceptance Evidence**
  - Recording: `[link-placeholder-phase1.mp4]`
  - Tests: `poetry run pytest -m unit`, `poetry run pytest -m contract`.

## Phase 2 — Customization & RAG

- **API Flow**
  1. Upload doc via `poetry run python -m chatbot.ingest upload ...`.
  2. Show `GET /admin/ingestion_jobs` status transitions.
  3. Demonstrate policy diff/publish endpoints.
- **Acceptance Evidence**
  - Recording: `[link-placeholder-phase2.mp4]`
  - Metrics: Grafana board `grafana.example.com/d/xin-ingestion`.

## Phase 3 — Frontend Enablement

- **UI Flow**
  1. `pnpm --prefix services/frontend dev` (or open staging console).
  2. Log in with seeded token, edit tenant metadata inline, create channel via wizard.
  3. Launch widget embed (served from `/embed.js`) and show bilingual toggle + offline banner.
- **Acceptance Evidence**
  - Recording: `[link-placeholder-phase3.mp4]`
  - Tests: `pnpm --prefix services/frontend e2e -- --headless`, `pnpm --prefix services/widget build`.

## Phase 4 — Hardening

- **Ops Flow**
  1. Run `make ci` (ensure 7-day green streak documented).
  2. Trigger `make demo DEMO_BASE_URL=https://staging.xinbot.ir ...` to showcase rebuild.
  3. Walk through incident handbook (`docs/RUNBOOK.md#8`) and highlight Grafana dashboards for latency/backups.
- **Acceptance Evidence**
  - Recording: `[link-placeholder-phase4.mp4]`
  - Tests: `poetry run locust ...` (load), `kubectl get pods` screenshot, Grafana `xin-ops` link.

> Keep this file updated after every milestone — include the latest recording link, CI run URL, and any deviations discovered during demo dry-runs.
