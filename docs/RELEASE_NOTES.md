# Release Notes

## Overview
This release introduces full observability, deployment automation, and containerized workflows for the Xin platform.

### Highlights
- Structured logging, Prometheus metrics, and OTLP tracing across orchestrator, channel gateway, and ingestion worker services.
- Multi-stage Docker builds plus a docker-compose stack for local parity.
- Helm chart with environment-specific values (staging/production) and automated smoke tests.
- GitHub Actions pipelines covering linting, type-checking, testing, image scanning, registry publishing, and Helm-based CD.
- Operational runbook documenting telemetry, secret management via Vault/Doppler, and post-deploy validation.

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
