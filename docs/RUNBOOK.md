# Xin Platform Runbook

## Observability Setup
- **Tracing**: Services call `chatbot.core.telemetry.init_tracing()` with OTLP exporter settings. Override via environment variables:
  - `OTEL_EXPORTER_ENDPOINT` (e.g. `http://otel-collector:4318/v1/traces`).
  - `OTEL_EXPORTER_HEADERS` for comma-delimited key=value pairs.
  - اگر مقداردهی نشود، لاگ هشدار `distributed tracing disabled; no OTLP endpoint configured` ثبت می‌شود و سرویس‌ها پیام `tracing disabled; operating without OTLP exporter` را در زمان راه‌اندازی درج می‌کنند.
  - در صورت موفقیت، لاگ‌های `tracing initialised` و `tracing active` تأیید می‌کنند که صادرکننده OTLP فعال است.
- **Metrics**:
  - FastAPI services expose Prometheus metrics at `/metrics`.
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
- Scenario defined in `tests/load/locustfile.py`; defaults to two brands with 50 concurrent conversations each and drives the full gateway → orchestrator → ingestion pipeline.
- Gateway traffic hits `/webchat/webhook` using HMAC signatures (`GATEWAY_WEBHOOK_SECRET`, default `dev-web`). Request names are tagged per-brand (e.g., `gateway:webhook:alpha`) so stats can be filtered quickly.
- Ingestion warmup periodically stages a markdown file via `/v1/brands/{brand_id}/knowledge`. Point Locust at the orchestrator with `ORCHESTRATOR_HOST=https://orch.dev`; it falls back to `LOCUST_HOST` when unset. Customize the seed file with `INGESTION_WARMUP_FILENAME|CONTENT|CONTENT_TYPE`.
- Every call emits a fresh `X-Request-ID`; Locust logs the correlation ID alongside the flow so failed requests can be traced in gateway/orchestrator logs.
- Execute headless load test: `make load-test`. Override the gateway host with `LOCUST_HOST=https://gateway.dev make load-test` and supply orchestrator/env overrides as needed.
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
- **Vault (staging sample in Helm values)**
  1. Provision an `ExternalSecret` backend by creating a `ClusterSecretStore` (e.g. `xin-vault-kv`) that points to the Vault KV path (`kv/data/xin/<env>`).
  2. Populate Vault with application key/value pairs (database credentials, LLM tokens, provider secrets). Reference keys in `deploy/helm/xin-platform/values-staging.yaml` under `externalSecrets.items`.
  3. Set `externalSecrets.enabled: true` when deploying and ensure the controller (ESO) is installed in the cluster. The rendered objects create Kubernetes `Secret`s (`xin-*-secrets`) that pods consume via `envFrom`.

- **Doppler (production example in Helm values)**
  1. Configure a Doppler `ClusterSecretStore` (`doppler-prod`) with a service token scoped to the production project.
  2. Maintain Doppler configs (`xin/platform/prod/*`) containing the required variables. The Helm `values-production.yaml` shows how to pull whole configs (`dataFrom.extract`) or individual keys.
  3. When `externalSecrets.enabled: true`, the controller reconciles Doppler secrets on a 30‑minute interval and surfaces them to workloads automatically.

- **Operational Notes**
  - Rotate credentials at source (Vault/Doppler); the External Secrets controller refreshes Kubernetes `Secret`s on the next sync.
  - Keep fallback `secretRefs` arrays available for legacy manual secrets, but prefer External Secrets for managed environments.
  - Align `*.secretRefs` in Helm values with the generated secret names (e.g. `xin-orchestrator-secrets`) so pods automatically project the synced data.
  - Restrict service tokens to least privilege and audit access routinely. Lock down CI secrets (`KUBE_CONFIG_*`, registry credentials) accordingly.

## Post-deploy Smoke Tests
- The CD workflow runs `scripts/smoke_test.sh` automatically after each Helm upgrade.
- To execute manually: `bash scripts/smoke_test.sh staging` (or `production`). Requires `kubectl` access and `helm` release name `xin-platform` deployed.
- The script waits for deployments to roll out and issues health probes from in-cluster curl jobs, ensuring service discovery and ingress routing function correctly.

### Smoke test script: sample output & troubleshooting

The `scripts/smoke_test.sh` script was enhanced to:

- Wait for all deployments that belong to the Helm release `xin-platform` to finish rolling out.
- Probe `/health` and `/metrics` for every Service attached to the release (it probes the first declared port).
- Optionally POST a small ingestion payload from inside the cluster if you set `INGESTION_URL`, and optionally poll an `INGESTION_VERIFY_URL` until it returns HTTP 200.

Usage examples

```bash
# basic
bash scripts/smoke_test.sh staging

# with ingestion enqueue + verify (example)
INGESTION_URL="http://xin-platform-xin-platform-orchestrator:8000/v1/brands/default/knowledge" \
INGESTION_PAYLOAD='{"title":"smoke","content":"hello"}' \
INGESTION_VERIFY_URL="http://xin-platform-xin-platform-orchestrator:8000/health" \
bash scripts/smoke_test.sh staging
```

Sample successful output

```
Using namespace=xin-staging release=xin-platform
Waiting for rollouts for deployments:
xin-platform-xin-platform-orchestrator
xin-platform-xin-platform-channel-gateway
Waiting rollout for deployment/xin-platform-xin-platform-orchestrator (timeout=180s)
deployment "xin-platform-xin-platform-orchestrator" successfully rolled out
Waiting rollout for deployment/xin-platform-xin-platform-channel-gateway (timeout=180s)
deployment "xin-platform-xin-platform-channel-gateway" successfully rolled out
Probing http://xin-platform-xin-platform-orchestrator:8000/health
OK: xin-platform-xin-platform-orchestrator:8000/health
Probing http://xin-platform-xin-platform-orchestrator:8000/metrics
OK: xin-platform-xin-platform-orchestrator:8000/metrics
Probing http://xin-platform-xin-platform-channel-gateway:8080/health
OK: xin-platform-xin-platform-channel-gateway:8080/health
Probing http://xin-platform-xin-platform-channel-gateway:8080/metrics
OK: xin-platform-xin-platform-channel-gateway:8080/metrics
Service probes (/health and /metrics) passed for release xin-platform in staging
POST succeeded
Ingestion verified (GET http://xin-platform-xin-platform-orchestrator:8000/health returned 200)
Smoke tests passed for staging
```

Troubleshooting

- kubectl permission denied / timed out waiting for rollout
  - Ensure your kubeconfig/current context has access to the target cluster and namespace.
  - Verify `kubectl get deployments -n <namespace>` works locally.
- No deployments/services found for the release
  - The script looks for the label `app.kubernetes.io/instance=xin-platform`. If your chart uses a different release name or labels, pass the expected environment or adjust the Helm release name variable inside the script.
- Probes failing for /metrics but /health works
  - `/metrics` may be exposed on a different port than the service's first port. Inspect the Service (`kubectl get svc -n <ns> <svc> -o yaml`) to confirm which port maps to metrics and override checks by calling the endpoint manually or adjusting the Service.
- curl image cannot be pulled inside cluster
  - The script uses `curlimages/curl`. Ensure the cluster can pull images from DockerHub, or change `IMAGE` in `scripts/smoke_test.sh` to a registry your cluster can access.
- Ingestion POST returns 4xx/5xx
  - Confirm the ingestion URL and payload schema. Check orchestrator logs for validation errors and use the returned correlation ID tie to traces.
- Ingestion verify timed out
  - The verify step polls until an HTTP 200. If ingestion is asynchronous and no single status endpoint exists, provide a specific `INGESTION_VERIFY_URL` that checks the item (for example an endpoint that lists the recently-uploaded item or a job status endpoint).

If you want me to further adapt the smoke test to your cluster (for example probing a specific metrics port per service or parsing job IDs from ingestion responses), tell me which endpoints your orchestrator exposes and I can wire an automated verification step.
