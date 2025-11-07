# Release Notes

## Overview
This release introduces full observability, deployment automation, and containerized workflows for the Xin platform.

### Highlights
- Structured logging, Prometheus metrics, and OTLP tracing across orchestrator, channel gateway, and ingestion worker services.
- Multi-stage Docker builds plus a docker-compose stack for local parity.
- Helm chart with environment-specific values (staging/production) and automated smoke tests.
- GitHub Actions pipelines covering linting, type-checking, testing, image scanning, registry publishing, and Helm-based CD.
- Operational runbook documenting telemetry, secret management via Vault/Doppler, and post-deploy validation.
- RAG alignment with Hooshpod reference: updated chunking defaults (512/64 overlap), OpenAI → sentence-transformer fallback, and enriched Qdrant metadata for tenant/brand filtering.

## Known Issues
- CI/CD and test targets rely on Poetry and containerized dependencies; ensure the runner installs Poetry prior to invoking `make` targets.
- Helm chart expects external secrets to exist (configured via `secretRefs`); deployments will fail without them.

## Compatibility
- Requires Python 3.11 images and Kubernetes 1.26+ for Helm chart features (apps/v1 deployments).
- Docker Compose v2.15+ recommended for BuildKit-based multi-stage builds.

## Upgrade Notes
1. Populate Doppler/Vault secrets and configure GHCR credentials before enabling CD workflow.
2. Run `docker-compose up --build` locally to verify service interop before pushing to main.
3. Execute `make verify` and `bash scripts/smoke_test.sh staging` to validate runtime environments post-upgrade.

### Differences vs. Hooshpod Reference
- Markdown chunker keeps semantic section detection and FAQ handling beyond the reference implementation while matching default chunk size/overlap.
- Embedding service supports OpenAI (primary) with automatic fallback to local sentence-transformers when keys or network access are unavailable; Hooshpod offered Xenova/Cohere selection.
- Qdrant integration namespaces vectors per tenant/brand and surfaces metadata for filtering; in-memory store retains same metadata for deterministic testing.

## This release (summary of changes)

This release adds several operational and CI improvements focused on safety, secrets management, observability defaults, and load-testing parity.

- CI enforcement and gates
	- New CI rules enforce linting, type checks, and a minimum test coverage threshold before images can be published. The GitHub Actions pipeline now fails merges when these checks are not satisfied.
	- The CD pipeline runs `scripts/smoke_test.sh` after Helm upgrades and will block promotion if the smoke tests fail.

- Migration smoke tests
	- Post-deploy smoke tests have been extended to wait for all rollouts in the Helm release, probe `/health` and `/metrics` on every service, and optionally enqueue a lightweight ingestion job to validate asynchronous pipelines.
	- These checks are performed in-cluster (using `kubectl run` + `curl`) to validate service discovery, DNS, and intra-cluster communication.

- External Secrets integration
	- The Helm charts were updated to integrate with External Secrets (Vault / Doppler examples remain in the runbook). The charts expect `externalSecrets.enabled` and `secretRefs` to be configured for production deployments.
	- Deployments without configured external secrets will fail early; the runbook documents how to seed the required secrets and the expected secret names.

- Telemetry defaults
	- Tracing and metrics are enabled by default at the application level but require an OTLP endpoint to be effective. The code logs explicit messages when tracing is disabled due to missing endpoints.
	- Metrics endpoints are standardized at `/metrics` for FastAPI services and prometheus scrape settings are documented in the runbook.

- Hooshpod parity findings
	- Chunking defaults have been tuned to match Hooshpod on size/overlap while keeping enhanced semantic section detection.
	- Embedding fallbacks (OpenAI → local sentence-transformer) were introduced to improve offline or keyless developer workflows; note behavioral differences in vector distributions compared to Hooshpod's runtime choices.

- Load testing upgrades
	- Locust scenarios were extended and made configurable; the headless `make load-test` target now allows overriding hosts and ramp rates via environment variables.
	- The smoke test and load test workflows are intended to be used together in pre-production to surface scaling and observability gaps before promotion.

## Remaining risks & mitigations

- Secrets and bootstrap ordering
	- Risk: Deployments that rely on External Secrets will fail if secrets are not provisioned prior to pod creation.
	- Mitigation: CI/CD should seed required secrets (or enable External Secrets controller) prior to Helm deployment. The runbook includes step-by-step preflight checks.

- Metrics port mismatches
	- Risk: `/metrics` may be served on a port other than the Service's first port; the smoke test probes the first port by default and may produce false negatives.
	- Mitigation: Review Service manifests to confirm port mapping; adjust the smoke script's `IMAGE` or per-service checks if necessary.

- Asynchronous ingestion verification
	- Risk: Enqueued ingestion may take longer than the smoke test timeout to appear in verification endpoints, causing flakes.
	- Mitigation: Provide a stable `INGESTION_VERIFY_URL` that checks job status (not just health). Increase `ENQUEUE_TIMEOUT` for slow backends.

- Telemetry sampling and visibility
	- Risk: If OTLP endpoints are misconfigured or blocked, tracing will be disabled and diagnosing production issues may be harder.
	- Mitigation: The services log explicit tracing status at startup; ensure collectors are reachable from the cluster and have permissive CORS/network rules for the test window.

---

If you'd like, I can add a pinned changelog entry with the release tag and date, or create a short checklist (preflight script) that CI can run before attempting deployments to reduce the 'secrets' and 'bootstrap ordering' risk above.
