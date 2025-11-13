# Xin ChatBot Delivery Roadmap

## 1. Vision
Deliver a tenant-ready conversational AI platform with self-serve onboarding, fully configurable policies, and a production-quality operator + end-user experience. This roadmap tracks the remaining work to: (1) finish the core backend capabilities, (2) bring the frontend to parity, and (3) harden operations for GA.

## 2. Guiding Principles
- **Tenant-first**: All flows must respect tenant isolation and configurability.
- **Automation with safeguards**: Every autonomous action must be explainable and reversible.
- **Operational readiness**: Documentation, monitoring, and runbooks ship alongside code.
- **Incremental releases**: Ship demonstrable value at each phase (MVP → Beta → GA).

## 3. Phase Overview
| Phase | Scope | Target | Definition of Done |
| --- | --- | --- | --- |
| Phase 1 — Admin Core | Tenant + channel CRUD, auth, policy scaffolding | Week 1–2 | Admin API live, tests cover CRUD paths |
| Phase 2 — Customization & RAG | Policy endpoints, ingestion APIs, retrieval tuning | Week 3–4 | Clients upload docs, manage ingestion jobs, diff/publish policies, and tune retrieval in-app |
| Phase 3 — Frontend Enablement | Operator console, embed widget, onboarding UI | Week 5–6 | Console manages tenants end-to-end |
| Phase 4 — Production Hardening | SSL, backups, monitoring, incident tooling | Week 7–8 | Meets runbook + SLO targets |
| Phase 5 — Optimization | Cost controls, analytics, advanced automations | Week 9–10 | Stretch goals post-GA |

## 4. Backlog by Stream
### 4.1 Backend
- Admin API (tenants, channels, secrets rotation)
- Policy config store with version history
- Knowledge ingestion service (async jobs, status endpoints)
- Automation scheduler with CRM/webhook actions
- Automation observability: metrics (`automation_queue_depth`, `automation_failures`), audit logs, bilingual-friendly operator controls
- Unified logging + tracing middleware

### 4.2 Frontend
- React operator console: tenant list, channel setup wizard, policy editor
- Web chat widget with theming + authentication handshake
- Client-facing onboarding checklist
- Visual diff + preview for prompts/policies

### 4.3 Platform Hardening
- Kubernetes manifests with autoscaling and PodDisruptionBudgets
- Systemd + Certbot playbooks for bare metal
- Monitoring dashboards + alerting rules (Grafana/Prometheus)
- Backup, restore, and DR playbooks validated quarterly
- Performance & resilience harness (`tests/perf/`, `scripts/chaos/`, `docs/perf/resilience_playbook.md`) exercising ≥5× load with chaos drills

## 5. Milestone Timeline
```
Week 1     Phase 1 kickoff   → Focus: tenant CRUD, auth, tokens
Week 2     Phase 1 complete  → Demo onboarding via API
Week 3     Phase 2 kickoff   → Focus: ingestion, retrieval configs
Week 4     Phase 2 complete  → Demo RAG customization + policy hooks
Week 5     Phase 3 kickoff   → Focus: operator console, embed widget alpha
Week 6     Phase 3 complete  → Demo UI onboarding (frontend parity)
Week 7     Phase 4 kickoff   → Focus: SSL, backups, observability runbooks
Week 8     Phase 4 complete  → Declare Production Candidate
Week 9–10  Phase 5           → Stretch tasks, stabilization, retros
```

## 6. Dependencies & Risks
- Credential management: Vault stories must land before multi-tenant GA.
- LLM provider limits: Implement fallback + rate limiting during Phase 2.
- Frontend resources: Requires dedicated FE dev during Weeks 5–6.
- Compliance reviews: Security sign-off needed before enabling automation at scale.

## 7. Success Metrics
- Time-to-onboard new tenant < 30 minutes end-to-end.
- 95% of automated replies accepted without manual intervention.
- < 1% ingestion jobs requiring manual retry.
- Postmortem ready within 48h of P1 incidents.

## 8. Release Log
| Release | Date | Highlights |
| --- | --- | --- |
| `v0.9.0-beta` | 2025-11-12 | Initial admin APIs, baseline docs | 
| `v0.10.0-beta` | 2025-12-03 | Backend `poetry run pytest` (612 tests @92% cov), Frontend `pnpm lint && pnpm e2e -- --headless`, Widget `pnpm build`; Grafana `xin-api-latency` dashboard attached; demo recording linked in `docs/demos/phase_walkthroughs.md#phase-2` |
| `v1.0.0-rc` | YYYY-MM-DD | Planned: frontend console + widget |
| `v1.0.0` | YYYY-MM-DD | Planned: hardened GA release |

## 9. References
- Architecture: `docs/ARCHITECTURE.md`
- Operations: `docs/RUNBOOK.md`
- Prompt packs: `docs/MASTER_PROMPTS_HARDENING.md` (backend/frontend prompts archived; see `docs/delivery/integrated_plan.md`)
