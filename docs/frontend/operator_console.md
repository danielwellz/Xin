# Phase 3 — Operator Console

![Operator console overview](../images/operator-console.svg)

## Overview

The `services/frontend` Vite + React console completes Phase 3 by exposing every operator workflow required in `docs/ROADMAP.md` and `docs/RUNBOOK.md §§5–7`. Bilingual UX (English + Persian) and RTL/LTR layout shifts are handled by the shared i18n bundle and Tailwind tokens.

## Features

| Surface | Highlights |
| --- | --- |
| Tenant Management | Global search, inline edits, channel overview, audit trail with scopes (`platform_admin`, `tenant_operator`). |
| Channel Wizard | Multi-step Instagram/Telegram/WhatsApp/Web setup, secret copy UX, webhook checklist mirroring Runbook §5. |
| Policy Editor | Schema-driven form + Monaco editor, diff viewer, diagnostics/test prompt wired to `/admin/diagnostics/retrieval`. |
| Knowledge Board | tus/resumable uploads, ingestion progress/logs, retry/cancel actions. |
| Automation Builder | Visual rule composer, live JSON preview, job status widget, pause/resume toggles. |
| Observability | Prometheus parser (latency, ingestion lag, automation queue) and Grafana snapshot embed hook. |

## Tooling & Commands

```bash
cd services/frontend
pnpm install
pnpm lint && pnpm test        # ESLint + Jest/RTL
pnpm storybook                # Component QA
pnpm dev                      # Local dev server (mock adapter optional)
pnpm e2e                      # Cypress smoke (English + Persian flows)
```

Quality gates:

- Lighthouse ≥90 (run `pnpm exec lhci autorun` after `pnpm build`).
- Cypress suite executes onboarding + policy publish flows in under 5 minutes.
- RTL snapshot review script: `pnpm exec cypress run --env locale=fa`.

## Deployment

- `pnpm build` writes artifacts to `services/frontend/dist`.
- Dockerfile `services/frontend/Dockerfile` packages the static bundle with Nginx.
- Docker Compose + Helm chart gained a `frontend` service referencing `/dist`, ensuring the operator console is served alongside backend services.

## Observability & Audit

- React Query surfaces request timing, with interceptors injecting `X-Trace-Id` plus tenant headers for trace correlation.
- Audit metadata is rendered inline with bilingual captions; RBAC toggles hide mutation controls when the scope is insufficient.
