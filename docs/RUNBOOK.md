# Xin Platform Runbook

## Observability Setup
- **Tracing**: Services call `chatbot.core.telemetry.init_tracing()` with OTLP exporter settings. Override via environment variables:
  - `OTEL_EXPORTER_ENDPOINT` (e.g. `http://otel-collector:4318/v1/traces`).
  - `OTEL_EXPORTER_HEADERS` for comma-delimited key=value pairs.
- **Metrics**:
  - FastAPI services expose Prometheus metrics at `/metrics`.
  - Channel Gateway exporter host/port: `GATEWAY_METRICS_HOST` / `GATEWAY_METRICS_PORT` (default `0.0.0.0:9102`).
  - Ingestion worker exporter host/port: `INGEST_METRICS_HOST` / `INGEST_METRICS_PORT` (default `0.0.0.0:9103`).
- **Logging**:
  - Structured JSON logging via `structlog`; correlation IDs emitted under `correlation_id`. Clients may pass `X-Request-ID` to preserve IDs.

### Troubleshooting Telemetry
- **No traces visible**: confirm `OTEL_EXPORTER_ENDPOINT` resolves and collector allows HTTP/protobuf. Logs show `tracing initialised` on success; errors are emitted once at startup.
- **Prometheus scrape fails**: ensure firewall allows the configured metrics port and scrape path `/metrics`. For ingestion worker exporter, confirm the process has not started twice—only the first invocation binds the port.
- **Missing correlation IDs**: verify middleware is active. Requests should include/receive `X-Request-ID` headers. If absent, confirm reverse proxy is not stripping headers.

## Test Strategy
- Run all suites with `make test`. Individual suites:
  1. `make test-unit` — quick validation with pytest marker `unit`.
  2. `make test-integration` — spins up testcontainers for orchestrator.
  3. `make test-contract` — verifies recorded webhook fixtures stay compatible.
- Coverage threshold is enforced at 85%. For local debugging, run `make coverage` to view term reports.
- Linting and type checks are available via `make lint` and `make typecheck`; combine with `make verify` before pushing.

### Common Test Failures
- **Integration tests hang**: Docker is required for testcontainers; ensure Docker daemon is running and not resource constrained.
- **Coverage drop**: confirm new modules are exercised by unit tests. Pytest skips directories lacking `__init__`? ensure tests import new code paths.

## Load Testing with Locust
- Scenario defined in `tests/load/locustfile.py`; defaults to two brands with 50 concurrent conversations each.
- Execute headless load test: `make load-test`. Override host with `LOCUST_HOST=https://gateway.dev make load-test`.
- Metrics and tracing remain enabled during load tests; monitor `/metrics` and collector dashboards.

### Load Test Issues
- **429/503 responses**: capture correlation IDs from logs and examine trace spans. Adjust Locust spawn rate via `--spawn-rate` if backend throttles.
- **High latency metrics**: inspect Prometheus histogram `http_request_latency_seconds` for offending routes. Cross-reference with tracing spans filtered by `service.name`.

## Incident Response Checklist
1. Check service `/health` endpoints for readiness.
2. Inspect `/metrics` for error spikes (`http_requests_total{status_code="5xx"}`).
3. Use correlation ID from problematic requests to pull logs and traces.
4. Validate downstream dependencies (Redis, Postgres, Qdrant) with connection dashboards; alerts propagate via telemetry metadata.

Keep this runbook in sync with infrastructure changes and expand troubleshooting tips as you learn from incidents.

## Secret Management
- **Vault** (production default):
  1. Store application secrets (database credentials, API tokens) under a dedicated KV path (e.g. `kv/xin/<env>`).
  2. Use an External Secrets controller or Vault Agent injector to project values into Kubernetes. Point the Helm values (`*.secretRefs`) at the generated secret names.
  3. Rotate credentials in Vault; workloads pick up changes automatically when the controller refreshes synced secrets.
- **Doppler** (developer convenience / staging):
  1. Maintain Doppler configs per environment; set required variables (`POSTGRES_*`, `OTEL_EXPORTER_OTLP_ENDPOINT`, etc.).
  2. Generate Kubernetes secrets with `doppler secrets download --format kubernetes > secret.yaml` and apply to the target namespace.
  3. Reference those secrets via `orchestrator.secretRefs`, `channelGateway.secretRefs`, and `ingestionWorker.secretRefs` in Helm overrides.
- Always scope service tokens to least privilege and audit access regularly. Update GitHub Actions with strict permissions for secrets (`KUBE_CONFIG_*`, registry credentials).

## Post-deploy Smoke Tests
- The CD workflow runs `scripts/smoke_test.sh` automatically after each Helm upgrade.
- To execute manually: `bash scripts/smoke_test.sh staging` (or `production`). Requires `kubectl` access and `helm` release name `xin-platform` deployed.
- The script waits for deployments to roll out and issues health probes from in-cluster curl jobs, ensuring service discovery and ingress routing function correctly.
