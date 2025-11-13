# Integrated Delivery Plan (Phases 1–4)

This plan aligns backend, frontend, and platform hardening streams on the path to GA. It mirrors `docs/ROADMAP.md`, enumerates DRIs, and ties verification, demos, and comms together.

## Milestone Board

| Phase | Target Window | Scope Highlights | Backend DRI | Frontend DRI | Platform/Infra DRI | Branch / Env | Acceptance Docs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Phase 1 — Admin Core** | Week 1–2 | Tenant/channels CRUD, JWT auth, baseline policies | Amir (Orchestrator Lead) | — | Leila (Infra) | `feature/phase-1-admin-core` → `dev` env | `docs/demos/phase_walkthroughs.md#phase-1`, API smoke via `scripts/demo_onboarding.py` |
| **Phase 2 — Customization & RAG** | Week 3–4 | Policy versions, ingestion APIs, retrieval tuning | Amir | — | Leila | `feature/phase-2-rag` → `staging` | Policy diff/publish demo recording, ingestion metrics Grafana link |
| **Phase 3 — Frontend Enablement** | Week 5–6 | Operator console, channel wizard, widget SDK | Amir | Sara (Frontend Lead) | Leila | `feature/phase-3-frontend` → `staging` UI env (`console.xinbot.local`) | Cypress + manual script in `docs/demos/phase_walkthroughs.md#phase-3`, embed snippet proof |
| **Phase 4 — Hardening** | Week 7–8 | TLS, backups, observability, incident prep | Amir | Sara | Nima (SRE Lead) | `release/phase-4-hardening` → `prod` candidate | Runbook updates (§3, §5, §8), Grafana dashboards + `make ci` streak logs |

Dependencies: Vault availability gates Phase 4, LLM quota upgrades gate Phase 2, dedicated FE capacity gates Phase 3. Cross-stream dependencies are logged in `docs/delivery/integrated_plan.md#risk-register`.

## Verification Matrix

| Layer | Command / Pipeline | Evidence |
| --- | --- | --- |
| Backend | `make lint typecheck coverage` (Poetry) | Stored in GitHub Actions `ci.yml` → job **backend** |
| Frontend Console | `pnpm --prefix services/frontend lint`, `pnpm ... test`, `pnpm ... e2e -- --headless` | GH Actions job **frontend** (push/pr + nightly) |
| Widget SDK | `pnpm --prefix services/widget test && pnpm --prefix services/widget build` | GH Actions job **widget** |
| Contract (API ↔ UI) | `poetry run pytest tests/contract/test_admin_ui_sync.py` | GH Actions job **contracts** |
| Prompt Pack Health | `poetry run python scripts/verify_prompts.py` | GH Actions job **backend** + scheduled nightly |
| Full-stack Aggregation | `make ci` | Required before tagging releases; run locally + GH job dependencies |
| Nightly Validation | `workflow_dispatch` + cron `0 6 * * *` for `ci.yml` schedule | Ensures prompts 1–5 remain green and Cypress smoke hits mocked backend |

## Demo Environments

- **dev**: `docker compose up` stack for fast iteration. Seed with `make demo ADMIN_TOKEN=<platform_admin_jwt>` (wraps `scripts/demo_onboarding.py` and prints the auto-generated embed snippet).
- **staging**: Kubernetes namespace referenced in `deploy/helm/xin-platform`. `make demo` can point to staging by overriding `DEMO_BASE_URL`.
- Tenants/Channels: `make demo` always provisions `Demo Tenant` + `Demo Web` channel and stores assets via ingestion CLI.
- Demo data resets: `make demo` is idempotent; call after updating migrations or frontend assets so recorded demos stay aligned.
- **Production deploys**: Follow `docs/delivery/vps_deploy.md` for the exact Xin VPS workflow (git pull, compose build, systemd restart, health checks).

## Team Rituals & Comms

- **Daily cross-stream standup (15 min @ 09:30 UTC)** — agenda: blockers, risk updates, demo readiness, CI health.
- **Thursday demo review** — run scripts in `docs/demos/phase_walkthroughs.md`, record Zoom, archive link in the same doc.
- **Status updates** — use `docs/comms/status_template.md`; send every Tuesday in `#xin-delivery`.
- **Stakeholder sign-off** — once QA checklist complete, capture approvals + action items in the template and link from `docs/ROADMAP.md#release-log`.

## Risk Register

| Risk | Impact | Owner | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Vault integration slips | Blocks multi-tenant secrets (Phase 4) | Nima | Track in Platform board; stub secrets via `.env` only in dev; escalate weekly | 🚧 Active |
| LLM quota exhaustion | Policy/prompt demos fail (Phase 2–3) | Amir | Configure fallback provider + rate limiter; watch `Grafana/xin-llm-quota` | 🟡 Monitoring |
| Frontend staffing gap | Phase 3 UI parity delayed | Sara | Documented scope + Storybook to onboard contractors; weekly FE sync | ✅ Mitigated |

## Documentation Checklist

- Architecture deltas → `docs/ARCHITECTURE.md` (Outstanding Gaps references this integrated plan).
- Runbooks → Update §§3, 5, 8 after each milestone.
- Demo scripts / screenshots → `docs/demos/phase_walkthroughs.md` and repo `docs/images`.
- Release notes → `docs/ROADMAP.md#release-log` per phase with CI + test evidence.

## Prompt & Hardening Alignment

`scripts/verify_prompts.py` enforces that `docs/MASTER_PROMPTS_HARDENING.md` still contains Prompts 1–5. The script runs in CI and nightly cron so any drift is visible before a phase is declared done (requirement: 7 consecutive green days).
