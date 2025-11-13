# Performance & Resilience Test Plan

This directory holds the artifacts used by the Performance & Resilience
engineering effort (Phase 4 hardening). It complements the existing Locust
suite in `tests/load/locustfile.py` with scripted workloads, channel mixes, and
chaos experiments that exercise the gateway, orchestrator, admin APIs, and
automation workers at ≥5× the expected traffic.

## Workload Model

`workload_mix.yaml` documents the assumed tenant/channel blend:

- 40 % Web widget, 25 % Instagram, 15 % Telegram, 10 % WhatsApp, 10 % automation.
- 3 ingestion jobs/minute per active tenant while spikes double the ingestion
  rate.
- Automation actions reference the webhook connector with CRM/e-mail fallbacks.

Update this file whenever new channels or traffic assumptions land; the k6
script loads the YAML at runtime to weight scenarios.

## Running k6-based API/Gateway Load

```bash
export GATEWAY_URL=https://gateway.xinbot.ir/webchat/webhook
export ORCHESTRATOR_URL=https://api.xinbot.ir
export ADMIN_TOKEN=<platform_admin_jwt>
export WEBHOOK_SECRET=<web secret from Vault>
export WORKLOAD_FILE_JSON=$(mktemp)
yq -o=json tests/perf/workload_mix.yaml > "$WORKLOAD_FILE_JSON"

k6 run tests/perf/orchestrator.js \
  --vus 250 \
  --duration 15m \
  -e GATEWAY_URL=$GATEWAY_URL \
  -e ORCHESTRATOR_URL=$ORCHESTRATOR_URL \
  -e ADMIN_TOKEN=$ADMIN_TOKEN \
  -e WEBHOOK_SECRET=$WEBHOOK_SECRET \
  -e WORKLOAD_FILE="$WORKLOAD_FILE_JSON"
```

Outputs:
- Custom metrics (`gateway_latency`, `orchestrator_latency`, `automation_latency`)
  emitted to stdout/JSON.
- CSV export by passing `--summary-export perf-summary.json`.

The script signs webhook payloads, posts admin ingestion jobs, and toggles
automation rules to ensure policy engine load. Thresholds align with SLOs:
`p(95)<1500ms`, `<1%` errors.

## Locust Spike / Warmup

The existing Locust profile remains convenient for interactive spikes:

```bash
LOCUST_TENANT_ID=<uuid> \
GATEWAY_WEBHOOK_SECRET=<secret> \
locust -f tests/load/locustfile.py --host https://gateway.xinbot.ir
```

Use this to validate secret rotation or reproduce customer-specific mixes.

## Chaos Experiments

Scripts under `scripts/chaos/` orchestrate the following scenarios:

| Script | Scenario | Notes |
| --- | --- | --- |
| `llm_latency.sh` | Injects latency/error into the LLM upstream via Toxiproxy | Observes policy fallback + alert firing |
| `redis_outage.sh` | Evicts Redis pods (Kubernetes) to test stream replay + rate limit cache loss | Expects auto-recovery <2 min |
| `qdrant_throttle.sh` | Applies network shaping (tc) or scales Qdrant replicas down | Ensures ingestion retry + API degradation alerts |
| `channel_spike.sh` | Temporarily scales gateway deployment to 5× traffic by launching additional k6 VUs | Validates HPA scaling & SLOs |

Each script only issues the orchestration commands (kubectl/toxiproxy); pair it
with the k6 load to stress the system while failures are injected.

## Reporting & Evidence

1. Export Grafana panels (API latency, ingestion lag, automation queue depth,
   gateway request rate) as PNG/CSV; attach to the sprint ticket.
2. Capture `kubectl describe hpa` before/after the test to prove scaling behaviour.
3. Record alert timelines (Alertmanager + Slack) and add them to
   `docs/perf/resilience_playbook.md`.
4. File remediation issues for any regression (autoscaling thresholds, connection
   pool tuning, queue depth) and link them in `docs/ROADMAP.md`.

## Future Extensions

- Add a k6 scenario generating admin onboarding flows (tenant creation) once the
  onboarding API stabilises.
- Integrate tests with GitHub Actions nightly, publishing summaries to
  `docs/ROADMAP.md#release-log`.
- Parameterise chaos scripts to run against staging and prod-like namespaces.
