# Xin Chatbot — Current Project Review

Date: 2025-11-07

This document captures the current project review and recommended, prioritized Phase 2 action plan for the Xin chatbot repository. It is a snapshot intended to be committed to the repo and used as the single source of truth for finishing Phase 2 and preparing Phase 3.

## High-level status

- Phase 1 (pilot foundation) — ✅ Completed
  - Core services, knowledge ingestion, RAG, guardrails, observability docs, and local/docker tooling are present.
  - Evidence: `src/` service code, `docs/RUNBOOK.md`, `scripts/smoke_test.sh`, `docs/RELEASE_NOTES.md`.

- Phase 2 (channel + action maturity) — ▶ In progress
  - Multi-channel adapters and action framework exist. Load testing and Locust scenarios exist.
  - Remaining work is mainly operational and CI/CD-focused:
    - Enforce `make verify` in CI
    - Add automated migration/smoke tests in CD (post-deploy)
    - Wire Helm charts with External Secrets (ESO) for production
    - Finalize telemetry defaults and verify behavior on missing OTLP endpoints
    - Expand/document Hooshpod parity and quick benchmarks

- Phase 3 (scale & production hardening) — ⏳ Not started
  - Advanced scaling strategies, heavy-data ingestion tuning, full cloud deploy automation, and performance dashboards remain future work.

## Rapid mapping: repo → roadmap
- CI checks / code quality: `pyproject.toml`, `Makefile`, `tests/` and `poetry` usage. `make verify` target exists (enforce in CI).
- Post-deploy validation: `scripts/smoke_test.sh` (updated to probe /health and /metrics, wait for rollouts, optional ingestion verify).
- Runbook & telemetry docs: `docs/RUNBOOK.md` (observability, telemetry notes, metrics endpoints).
- Helm charts: `deploy/helm/xin-platform/*` — needs external secrets wiring and values review.
- Load testing: `tests/load/locustfile.py` and `Makefile` targets — configurable via env vars.

## Prioritized Phase 2 action plan (concrete tasks)

Note: small effort items first to reduce deployment risk.

Priority A — Blockers (high urgency)

A1. Enforce `make verify` in CI
- What: Add `make verify` as a required step in GitHub Actions (or CI runner). Ensure Poetry is available before running.
- Acceptance: PRs that fail lint/tests/coverage are blocked by branch protection.
- Effort: 1–2 hours.

A2. Add a preflight check script and run in CI/CD
- What: `scripts/preflight_check.sh` that validates: `helm template` renders, required External Secrets exist (if enabled), and `kubectl` namespace access if applicable.
- Acceptance: Preflight returns non-zero and stops deploy when checks fail; CI uses it before `helm upgrade`.
- Effort: 2–3 hours.

Priority B — Post-deploy validation (automated smoke tests)

B1. Wire `scripts/smoke_test.sh` into CD (post-helm-upgrade)
- What: After `helm upgrade --install`, run the smoke test and fail the pipeline on error. Save logs/artifacts.
- Acceptance: Failed smoke tests cause CD to fail and stop promotion.
- Effort: 1–2 hours.

Priority C — Secrets & telemetry hygiene

C1. Wire Helm values to External Secrets controller (ESO)
- What: Update `values-*.yaml` and docs to enable `externalSecrets.enabled` where appropriate and document ESO installation (ClusterSecretStore + ExternalSecret examples)
- Acceptance: Production deploys succeed because secrets are provisioned by ESO and pods start with the required env vars.
- Effort: 2–4 hours (ops + docs).

C2. Finalize telemetry defaults and verification
- What: Ensure services log clear tracing status on startup and that `/metrics` is reachable by smoke tests. Add a CI container-start test (optional) to validate telemetry startup logs.
- Acceptance: Each service logs either `tracing initialised` or `tracing disabled; no OTLP endpoint configured` and `/metrics` responds to a curl probe.
- Effort: 2–6 hours depending on required code changes.

Priority D — Documentation / parity

D1. Expand Hooshpod parity docs and quick benchmarks
- What: Add a short notebook or unit tests showing embedding differences on a representative corpus and document behavior differences.
- Acceptance: An `examples/hooshpod-parity.md` or notebook added with results.
- Effort: 2–4 hours.

## Acceptance checklist for Phase 2

- [ ] `make verify` enforced in CI and required for PR merges
- [ ] `scripts/preflight_check.sh` exists and is used in CD pre-deploy
- [ ] CD runs `scripts/smoke_test.sh` after Helm upgrades and fails on errors; logs stored
- [ ] Helm values and runbook updated for External Secrets usage; ESO installation documented
- [ ] Telemetry startup behavior documented and verified; `/metrics` is scrapped by smoke tests
- [ ] Hooshpod parity documentation and basic benchmarks included in `docs/` or `examples/`

## Sample CI snippets

GitHub Actions: enforce `make verify` (add this step to your CI job that runs on PRs):

```yaml
- name: Install dependencies
  run: poetry install --no-root

- name: Run verify
  run: make verify
```

GitHub Actions: CD post-deploy smoke test (run after `helm upgrade` step):

```yaml
- name: Run smoke tests
  env:
    KUBECONFIG: ${{ secrets.KUBE_CONFIG }}
    INGESTION_URL: ${{ secrets.INGESTION_URL }} # optional
    INGESTION_VERIFY_URL: ${{ secrets.INGESTION_VERIFY_URL }} # optional
  run: bash scripts/smoke_test.sh staging
```

## Example `scripts/preflight_check.sh` (starter)

```bash
#!/usr/bin/env bash
set -euo pipefail

NAMESPACE=${1:-xin-staging}
RELEASE=${2:-xin-platform}

# render helm chart
helm template ${RELEASE} deploy/helm/xin-platform --values deploy/helm/xin-platform/values-staging.yaml >/dev/null

# if External Secrets enabled, ensure required secrets exist (example name)
if helm template ${RELEASE} deploy/helm/xin-platform | grep -q "externalSecrets.enabled: true"; then
  if ! kubectl get ns ${NAMESPACE} >/dev/null 2>&1; then
    echo "Namespace ${NAMESPACE} not found"
    exit 1
  fi
  # example check -- adapt secret names as needed
  kubectl get secret xin-orchestrator-secrets -n ${NAMESPACE} >/dev/null
fi

echo "Preflight checks passed"
```

> Note: The preflight script above is a starter. Adjust checks to match your real `values-*.yaml` and secret naming scheme.

## Remaining risks & mitigations (recap)

- Secrets and bootstrap ordering: mitigate with preflight seed checks or a job that ensures ESO is installed and secrets are seeded.
- `/metrics` port mismatches: mitigate by making metric-port mapping configurable in smoke tests or mapping it in Helm values.
- Asynchronous ingestion verification flakiness: mitigate by using job-status endpoints, increasing timeouts, or building a test-only synchronous endpoint.
- Telemetry sampling/visibility: ensure OTLP endpoints are reachable and startup logs are monitored; add alerting for disabled tracing if required.

## Next recommended implementation steps (I can implement any of these for you)
1. Create `scripts/preflight_check.sh` and wire it into the CD pre-deploy stage (I estimate 2–3 hours).
2. Add the CI snippet to enforce `make verify` on PRs (1 hour).
3. Wire `scripts/smoke_test.sh` to CD and ensure logs are archived (1–2 hours).
4. Add a small `examples/hooshpod-parity.md` showing benchmark snippets (2–4 hours).

If you want me to implement step 1 or step 2 now, tell me which one and I'll add the script and/or CI YAML and update the repo.

---

(Generated by repo review on 2025-11-07)
