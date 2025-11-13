# QA Strategy — GA Readiness

This folder centralizes the QA artefacts needed for the Phase 4 hardening
milestone. Use it alongside `docs/RUNBOOK.md` and the regression suite in
`tests/` to prove release candidates meet the SLO + coverage gates.

## Contents

| File | Purpose |
| --- | --- |
| `regression_plan.md` | Feature-to-test mapping, data seeding plan, coverage/alert expectations. |
| `release_checklist.md` | Pass/fail template capturing command outputs, coverage %, migration diffs, and manual exploratory sign-offs. |

## High-level Workflow
1. **Prep data:** Seed at least two tenants and four channels using the admin API
   (`scripts/demo_onboarding.py` or manual curls). Ensure Vault secrets are set
   up so channel webhooks can be exercised end-to-end.
2. **Automated runs:** Execute `poetry run pytest` (backend), `pnpm --prefix services/frontend test && pnpm --prefix services/frontend e2e -- --headless`
   (frontend), and widget CI. Export coverage via `poetry run coverage xml` and
   `pnpm --prefix services/frontend test -- --coverage`.
3. **Migration drill:** Follow the steps in `regression_plan.md§3` to run
   upgrade/downgrade tests on a snapshot database; attach the diff/rollback log.
4. **Alert validation:** Trigger latency/backlog alerts using the chaos scripts
   in `scripts/chaos/` and record Alertmanager payloads plus Grafana snapshots.
5. **Manual sweeps:** Execute exploratory passes on operator console + widget,
   logging bugs (severity, owner, status). Reference them in the release
   checklist.
6. **Finalize report:** Populate `release_checklist.md` with the collected
   evidence, coverage numbers, and outstanding waivers. Store artefacts
   (`coverage.xml`, `k6` summaries, Cypress videos) under `docs/demos/perf/<date>/`.

QA owns the go/no-go recommendation after verifying every box in the checklist.
