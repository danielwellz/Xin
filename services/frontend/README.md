## Xin Operator Console (Phase 3)

> React + Vite + TypeScript console covering tenant ops, channel provisioning, policies, knowledge, automations, and observability with bilingual UX.

### Getting Started

```bash
cd services/frontend
pnpm install
pnpm dev        # http://localhost:4173
pnpm lint       # ESLint (flat config)
pnpm test       # Jest + RTL
pnpm storybook  # Component workbench
pnpm e2e        # Cypress smoke suite (requires `pnpm dev` in another shell)
```

- React Query powers the data layer; an in-memory Axios adapter serves mock responses when `VITE_USE_MOCKS=true`.
- Tailwind + CSS variables enforce design tokens and RTL-safe spacing.
- Locale toggle persists in `localStorage` (`en` ↔ `fa`), updating document `dir`.
- Auth flow expects JWTs issued via `/admin/tokens`; paste token on the sign-in screen or preload `xin-operator-token` in `localStorage`.
- Headers include JWT, `X-Tenant-ID`, and `X-Trace-Id` for parity with backend middleware.

### Key Features

1. **Tenant management** – list/search, inline edit, audit trail, channel overview.
2. **Channel wizard** – multi-step Instagram/Telegram/WhatsApp/Web provisioning with webhook instructions mirroring `docs/RUNBOOK.md §§5–7`.
3. **Policy editor** – schema-driven form, Monaco JSON editing, diff viewer, diagnostics/test prompt actions.
4. **Knowledge board** – tus/resumable uploads, ingestion jobs/log viewer, retry controls.
5. **Automation builder** – visual composer, live JSON preview, job monitor, pause/resume toggles.
6. **Observability** – Prometheus metric parsing plus optional Grafana snapshot embed (`VITE_GRAFANA_SNAPSHOT_URL`).

### Environment

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Orchestrator base URL override (prod defaults to `window.location.origin`, local fallback `http://localhost:8000`). |
| `VITE_USE_MOCKS` | `true` to bootstrap the in-memory Axios mock adapter for UI-only iteration. |
| `VITE_TUS_ENDPOINT` | Optional tus endpoint for large asset uploads. |
| `VITE_GRAFANA_SNAPSHOT_URL` | Optional iframe source for Grafana snapshots. |

### Quality Gates

- Lighthouse PWA matrix scripted via `pnpm run e2e` + `pnpm exec lhci autorun` (see docs/frontend/operator_console.md).
- Cypress suite validates onboarding + policy publish flows in both locales (<5 minutes).
- Jest/RTL covers locale toggles, Prometheus parsing, and future component stories.

### Build & Deploy

Produces static assets under `services/frontend/dist`. Dockerfile ships a multi-stage Node → Nginx image and Helm/Docker Compose now reference the artifact for `xin_frontend`.
