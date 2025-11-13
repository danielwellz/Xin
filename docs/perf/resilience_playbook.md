# Performance & Resilience Playbook

_Last updated: 2025-11-13_

This playbook defines the workload assumptions, load tests, and chaos drills
required to prove Xin ChatBot meets the SLOs in `docs/RUNBOOK.md §2` during
Phase 4 hardening.

## 1. Workload Assumptions
- Channel mix (per `tests/perf/workload_mix.yaml`):
  - Web widget 40 %, Instagram 25 %, Telegram 15 %, WhatsApp 10 %, automation 10 %.
  - Two active tenants with mixed brands; each brand sustains 30–50 concurrent
    conversations during spikes.
- Ingestion: 3 jobs/minute/tenant under normal conditions; spikes double the
  rate for 10 minutes following knowledge uploads.
- Automation: 5 triggers/minute/tenant with 60 % webhook, 20 % CRM, 20 % email.

## 2. Load Tests

### 2.1 Gateway + Orchestrator (k6)
Command:
```bash
yq -o=json tests/perf/workload_mix.yaml > /tmp/workload.json
GATEWAY_URL=https://gateway.xinbot.ir/webchat/webhook \
ORCHESTRATOR_URL=https://api.xinbot.ir \
ADMIN_TOKEN=<platform_admin_jwt> \
WEBHOOK_SECRET=<web_secret> \
WORKLOAD_FILE=/tmp/workload.json \
k6 run tests/perf/orchestrator.js --vus 250 --duration 15m --summary-export perf-summary.json
```
Expectations:
- `gateway_latency` and `orchestrator_latency` P95 < 1.5 s.
- `http_req_failed` < 1 %.
- Automation/test endpoints remain < 5 s even when webhook latency injected.

### 2.2 Locust Smoke / Spike
```bash
locust -f tests/load/locustfile.py --host https://gateway.xinbot.ir \
  --users 500 --spawn-rate 100
```
Used for ad-hoc verification during release rehearsals.

## 3. Chaos Experiments

| Scenario | Script | Verification |
| --- | --- | --- |
| LLM latency / timeout | `scripts/chaos/llm_latency.sh` | Policy fallback fires; Alertmanager `HighLatencyLLM` alert; traces show alternate model used |
| Redis outage | `scripts/chaos/redis_outage.sh` | Gateway/orchestrator retry and recover < 2 min; `automation_queue_depth` stays < 50 |
| Qdrant degradation | `scripts/chaos/qdrant_throttle.sh` | Ingestion jobs retry/backoff; API latency increases but alert triggers < 1 min |
| Channel spike | `scripts/chaos/channel_spike.sh` | Gateway/orchestrator HPAs scale to max replicas; `kubectl describe hpa` shows desired replicas increase |

For each scenario:
1. Start k6 load (Section 2.1) with baseline metrics captured.
2. Run the chaos script (ensuring the right namespace/proxy variables).
3. Capture Grafana screenshots (API SLOs, ingestion lag, automation queue depth,
   widget/gateway logs) and attach to the incident template.
4. Record Alertmanager timeline (fired/resolved) and compare to SLO requirements.
5. Document recovery time and any manual interventions.

## 4. Metrics & Evidence
- Export metrics via `k6 --summary-export` and Grafana CSV downloads:
  - API latency panel
  - Gateway request rate
  - Ingestion lag stat (`Xin Ingestion Health`)
  - Automation queue depth
- Capture Kubernetes scaling events: `kubectl -n xin-prod describe hpa`.
- Store artifacts under `docs/demos/perf/<date>/`.

## 5. Tuning Loop
1. If load tests breach thresholds:
   - Increase orchestrator/gateway CPU limits or concurrency.
   - Adjust DB/Redis pool sizes via environment variables.
   - Modify HPA targets (`deploy/helm/xin-platform/values*.yaml`).
2. Update alert thresholds in `deploy/observability/alerting/rules.yml` when new
   baselines are established.
3. Add remediation tasks to `docs/ROADMAP.md` (Phase 4) with owners + due dates.

## 6. Reporting
- Summaries go into the weekly status update plus `docs/ROADMAP.md#release-log`.
- Include: command output, Grafana screenshots, Alertmanager links, Kubernetes
  scaling evidence, and follow-up tickets.
- Archive chaos rehearsal notes with timestamps and observed recovery time.
