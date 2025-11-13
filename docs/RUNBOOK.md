# Xin ChatBot Runbook

_Last updated: $(date +%Y-%m-%d)_

## 1. Service Ownership
- **Primary**: Platform Team — `platform@xinbot.ir`
- **Secondary**: Automation Team — `automation@xinbot.ir`
- **Pager Rotation**: `@xinbot-oncall` in Slack

## 2. Operational SLOs
| Metric | Target | Page When |
| --- | --- | --- |
| API availability | 99.5% rolling 30d | 5 min error budget burn |
| P95 latency | < 1.2 s | 3 consecutive datapoints above 1.5 s |
| Ingestion lag | < 10 min | Any tenant > 30 min |
| Automation jobs | 0 stuck jobs | Queue depth > 50 for 10 min |

## 3. Pre-flight Checklist (Release Day)
1. `make ci` — aggregates backend lint/tests, frontend lint/unit/Cypress, widget build, prompt verification, and contract tests. Require a 7-day green streak in `.github/workflows/ci.yml`.
2. `docker compose build` (or CI pipeline) — ensure images tagged `xin-<date>`; attach workflow links to release notes.
3. Verify migrations: `alembic upgrade head` in staging; confirm seeded tenant via `make demo ADMIN_TOKEN=<platform_admin_jwt>`.
4. Run smoke tests: `poetry run python -m chatbot.cli --tenant-id <test>` plus `pnpm --prefix services/frontend e2e -- --headless`.
5. Update release notes in `docs/ROADMAP.md#release-log` with build hashes, Grafana dashboard links, and demo recording references.
6. Send stakeholder update using `docs/comms/status_template.md`, linking to the relevant section in `docs/demos/phase_walkthroughs.md`.
7. Follow the detailed VPS deployment steps in `docs/delivery/vps_deploy.md` when promoting builds to xinbot.ir.

## 4. Deployment Procedures
### 4.1 Docker Compose (Dev/Staging)
```bash
make deploy-dev                       # wraps scripts/deploy/deploy_dev.sh
open https://localhost:8443/docs      # served via Caddy (self-signed, HSTS)
open http://localhost:3000            # Grafana (Prometheus/Tempo/Loki stack)
```
The helper script copies `deploy/compose/.env.dev.example` on first run, issues
self-signed TLS via Caddy, boots observability (`prometheus`, `tempo`, `loki`,
`grafana`, `promtail`), applies Alembic migrations, and waits for
`https://localhost:8443/health`.

Validation checklist:
- `curl -k https://localhost:8443/health`
- `curl -k https://localhost:8443/webhooks/health`
- `docker compose --env-file deploy/compose/.env.dev -f docker-compose.yml -f deploy/observability/docker-compose.yml ps`
- Grafana dashboards (`http://localhost:3000`) show data for API / ingestion / automation panels.

Bare-metal installs use the systemd units in `deploy/systemd/`. Install them via
`sudo cp deploy/systemd/xin-*.service /etc/systemd/system/ && sudo systemctl enable --now ...`.
TLS certificates are handled by `scripts/tls/bootstrap_certbot.sh` (initial issue)
and `scripts/tls/renew_certificates.sh` (cron/timer friendly).

### 4.2 Kubernetes (Prod)
1. `kubectl apply -k deploy/overlays/prod`
2. `kubectl rollout status deploy/xin-xin-platform-orchestrator && kubectl rollout status deploy/xin-xin-platform-channel-gateway`
3. `kubectl get hpa,pdb -n xin-prod | rg xin-platform`
4. `kubectl logs deploy/xin-xin-platform-orchestrator -c orchestrator --since=10m`
5. `kubectl describe ingress xin-xin-platform` (TLS, HSTS, cert-manager annotations)
6. Post release summary in Slack with image tags, migration IDs, and Grafana screenshot links.

## 5. Run-Time Operations
### 5.1 Tenant Onboarding
1. `POST /admin/tenants` with payload from onboarding form.
2. `POST /admin/channels` per channel; store returned secrets in Vault.
3. Generate web embed snippet via `/admin/tenants/{id}/embed_snippet` (temporary curl if UI not ready).
4. Upload starter knowledge pack through knowledge ingestion CLI or portal.

Example commands (replace `$ADMIN_TOKEN` and IDs accordingly):

```bash
curl -sS -X POST http://localhost:8000/admin/tenants \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Support",
    "timezone": "UTC",
    "metadata": {"plan": "enterprise"},
    "embed_theme": {"primary": "#ff3366"}
  }'

curl -sS -X POST http://localhost:8000/admin/channels \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "TENANT_UUID",
    "brand_name": "Acme",
    "channel_type": "web",
    "display_name": "Web Widget",
    "credentials": {"webhook_url": "https://hooks.acme.com/xin"}
  }'

curl -sS http://localhost:8000/admin/embed_snippet/TENANT_UUID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Use `scripts/demo_onboarding.py --api-token $ADMIN_TOKEN` for an automated smoke test that performs these calls end-to-end.

#### 5.1.1 Client Embed (`/embed.js`)
- Serve the signed widget SDK from `services/widget/dist/embed.js` (Docker/Helm expose it via the `frontend` service).
- Generate short-lived tokens: `POST /admin/tenants/{id}/embed_token` optionally supplies end-user identity metadata; tokens are kept in-memory by the widget and expire within minutes.
- Drop-in snippet (bilingual, RTL aware):

  ```html
  <script
    defer
    src="https://console.xinbot.ir/embed.js"
    data-tenant="TENANT_UUID"
    data-api="https://api.xinbot.ir"
    data-gateway="wss://gateway.xinbot.ir"
    data-locale="fa">
  </script>
  ```

- React hosts can install `@xin-platform/widget-sdk` and wrap their tree:

  ```tsx
  import { XinWidgetProvider } from "@xin-platform/widget-sdk/react";

  export function App() {
    return (
      <XinWidgetProvider
        options={{
          tenantId: "TENANT_UUID",
          apiBaseUrl: "https://api.xinbot.ir",
          gatewayUrl: "wss://gateway.xinbot.ir",
          locale: "en"
        }}
      >
        <YourApp />
      </XinWidgetProvider>
    );
  }
  ```

- Offline fallback: when orchestrator/gateway is unreachable the banner `offline` string is displayed (localized), outbound messages are queued, and telemetry records retries. Document this plain HTML experience when working with WebView hosts.

### 5.2 Knowledge Ingestion
- Queue files with `poetry run python -m chatbot.ingest --tenant-id ... --path ...`
- Monitor ingestion worker logs: `docker logs xin_ingestion_worker -f | rg tenant_id`
- If stuck, `DELETE /admin/ingestion_jobs/{id}` then requeue.
- `POST /admin/knowledge_assets/upload` registers assets (tags + visibility) and enqueues jobs. Inspect state with `GET /admin/knowledge_assets?tenant_id=<uuid>` and `GET /admin/ingestion_jobs?tenant_id=<uuid>`.
- CLI shortcuts: `python -m chatbot.ingest upload --tenant-id <uuid> --brand-id <uuid> --file docs/faq.md --api-token $ADMIN_TOKEN` and `python -m chatbot.ingest jobs --tenant-id <uuid> --api-token $ADMIN_TOKEN`.

### 5.3 Automation Policies & Jobs
- Manage rules via `/admin/automation/rules` (CRUD + pause/resume) or CLI `python -m chatbot.automation rules --api-token $ADMIN_TOKEN`.
- Test actions with `POST /admin/automation/test` before activating.
- Observe executions: `GET /admin/automation/jobs?tenant_id=<uuid>`; retry/cancel jobs via `/admin/automation/jobs/{id}/retry|cancel`.
- Automation worker: `python -m chatbot.automation.worker` (ships APScheduler + Prometheus metrics). Ensure `AUTOMATION_QUEUE_DEPTH`, `AUTOMATION_FAILURES` stay within SLO.

### 5.4 Secret Rotation & Credential Hygiene
- **Channel/API secrets**: rotate quarterly (or immediately after suspected compromise) via the admin API once the rotation endpoint is live (`docs/security/2025-11-13-ga-review.md`). Until automation ships, coordinate with Platform to reissue secrets in Vault and update the gateway env vars.
- **Admin JWT signing key**: stored only in Vault (`secret/data/xin/<env>/admin`). Update `ADMIN_JWT_SECRET` and restart orchestrator; keep old key for 15 minutes to drain sessions.
- **Webhook HMAC**: keep provider shared secrets in Vault; never rely on `.env.dev` defaults in staging/prod.
- Track rotations in the Ops calendar and attach evidence (Vault version, Alertmanager quiet) to weekly status updates.

## 6. Monitoring & Alert Response
| Alert | Immediate Actions |
| --- | --- |
| `ApiErrorBudgetBurn` | Review Grafana `Xin API SLOs` (panel: Error Rate), compare against `/metrics` to confirm; tail `xin-orchestrator` logs via Loki for shared tenant/channel failures; roll back recent deploy if regression |
| `ApiLatencyP95Breached` | Check `histogram_quantile` panel plus Tempo traces; confirm upstream LLM latency; scale orchestrator HPA max if CPU saturated (`kubectl edit hpa xin-xin-platform-orchestrator`) |
| `GatewayHealthCheckFailed` | `kubectl logs deploy/xin-xin-platform-channel-gateway -c channel-gateway`; verify ingress is routing TLS traffic and channel webhooks still hitting CDN |
| `IngestionLagHigh` | Inspect Grafana `Xin Ingestion Health`, then `kubectl top pods -l app.kubernetes.io/component=ingestion-worker`; temporarily scale deployment to 4 replicas and confirm MinIO/object storage reachable |
| `AutomationBacklog` | Validate queue depth panel + Prometheus alert context; pause noisy automation rules via `/admin/automation/rules/{id}/pause`, scale `xin-xin-platform-automation-worker`, then resume once backlog < 10 |
| `AutomationFailuresSpike` | Compare Loki log stream for `automation` container vs Alertmanager payload; retry failed jobs with `/admin/automation/jobs/{id}/retry` and capture root cause for postmortem |

Grafana dashboards (auto-provisioned from `deploy/observability/grafana/`) map
one-to-one with on-call workflows:
- **Xin API SLOs** — primary view for latency/error budget alerts.
- **Xin Ingestion Health** — backlog proxy + per-tenant inflight counts.
- **Xin Automation Health** — queue depth, latency, worker failures.
- **Widget & Gateway** — request rate and Loki-powered log tail for adapters.

Alertmanager (port `9093`) routes everything to Slack/webhooks defined in
`deploy/observability/alertmanager.yml`. Update the receiver URL when the
incident bridge changes and paste the Alertmanager permalink into postmortems.
Loki retention is set to seven days (`deploy/observability/loki-config.yml`);
increase `limits_config.retention_period` before high-volume launches.

## 7. Troubleshooting Playbooks
### 7.1 Webhook Failures
1. Inspect request log: `kubectl logs deployment/xin-gateway | rg <channel_id>`
2. Validate signature using stored HMAC secret.
3. Replay a payload with `scripts/replay_webhook.py payload.json`.
4. If 4xx returned, fix tenant/channel configuration; if 5xx, capture stack trace and escalate.

### 7.2 Retrieval Relevance Issues
1. Run `scripts/debug_retrieval.py --tenant-id ... --query "..."`.
2. Compare embeddings between OpenAI and fallback (see `docs/ARCHITECTURE.md`).
3. Ensure ingestion job status is `completed` and document metadata contains `visibility=public`.
4. Reduce or raise similarity threshold via policy flag `retrieval.min_score`.
5. Use diagnostics: `python -m chatbot.debug.retrieval --tenant-id <uuid> --brand-id <uuid> --query "Reset hub"` (wraps `POST /admin/diagnostics/retrieval`).
6. Tune retrieval config via `PUT /admin/policies/{tenant_id}/retrieval_config` (fields: `hybrid_weight`, `min_score`, `max_documents`, `context_budget_tokens`, `filters`, `fallback_llm`).

### 7.3 Automation Misfires
- Check APScheduler dashboard (`/ops/automation`).
- Validate cron spec stored under tenant automation config.
- Clear stuck job row in Postgres table `automation_jobs`.
- Use diagnostics CLI: `python -m chatbot.automation simulate --tenant-id <uuid> --rule-id <uuid> --api-token $ADMIN_TOKEN`.
- Retry or cancel via `/admin/automation/jobs/{id}/retry`/`/cancel`; confirm status flips to `pending`/`cancelled`.

## 8. Incident Management
1. Declare incident in Slack `#xin-incident` with severity.
2. Assign Incident Commander (IC) and scribe. Loop in `security@xinbot.ir` for any auth/secret related events; they hold the Vault unseal tokens.
3. Update status page every 30 minutes and ensure GuardDuty/Alertmanager notifications are acknowledged.
4. After mitigation, capture timelines + root cause in postmortem doc; store under `docs/incidents/<date>.md`. Attach relevant Grafana/Alertmanager links and any secret rotations performed.
5. Post summary + action items in the weekly status update (template: `docs/comms/status_template.md`) and review during the next cross-stream standup (09:30 UTC, Monday–Thursday).

## 9. Maintenance Windows
- Weekly Wednesday 02:00–03:00 UTC: OS patching, database vacuum.
- Monthly first Sunday: rotate API secrets, regenerate TLS certs.
- Quarterly: failover rehearsal between active and standby region.

## 10. Backup & Restore
- Nightly cron (02:30 UTC) executes `scripts/backups/create_backup.sh` on the
  staging controller with `ENV_FILE=/opt/xin-chatbot/config/prod.env` and
  `BACKUP_BUCKET=xin-db-backups`. The script captures:
  1. `pg_dump -Fc` for Postgres (retention: 30 days in S3).
  2. A full Qdrant snapshot via the `/snapshots` API.
  3. A MinIO/object-storage sync (downloaded locally then bundled).
- Archives are stored as `xin-backup-<timestamp>.tar.gz` under
  `s3://xin-db-backups/`.
- Object-storage credentials must be provided through the env file (never stored
  in git). AWS/MinIO credentials come from Vault / ExternalSecrets.

### 10.1 Manual backup (ad-hoc)
```bash
ENV_FILE=/opt/xin-chatbot/config/prod.env \
BACKUP_BUCKET=xin-db-backups \
./scripts/backups/create_backup.sh
```
Verify the tarball exists locally and in S3, then log the timestamp in the
release notes.

### 10.2 Restore rehearsal (quarterly)
```bash
poetry run python scripts/restore_from_backup.sh --timestamp 20250110T120000Z \
  --env-file /opt/xin-chatbot/config/staging.env --bucket xin-db-backups
```
- Script extracts the archive, runs `pg_restore --clean`, uploads the Qdrant
  snapshot via `POST /snapshots/upload`, and rehydrates the object storage
  bucket through the MinIO endpoint.
- After restore, run comparison queries (`SELECT count(*) FROM conversations`
  etc.) between staging + prod snapshots to validate < 1% delta.
- Document each rehearsal (timestamp, duration, verification queries) in
  `docs/demos/phase_walkthroughs.md` and link from the weekly status update.

## 11. Decommissioning a Tenant
1. Disable automations via API.
2. Archive transcripts and knowledge assets to S3/archive bucket.
3. Delete tenant-specific secrets from Vault and invalidate webhook tokens to prevent replay.
4. Soft delete tenant row (`deleted_at` timestamp) to maintain referential integrity; retain hashed secrets only for audit purposes.
5. Log the teardown in `admin.events` and notify `security@xinbot.ir` so they can scrub any lingering secrets from monitoring dashboards.

## 12. Contacts & Escalations
| Scenario | Contact |
| --- | --- |
| Auth / Identity | `security@xinbot.ir` |
| Data Platform | `data@xinbot.ir` |
| Cloud Infra | `infra@xinbot.ir` |
| Client Success | `success@xinbot.ir` |

## 13. Appendix
- CLI tips: `poetry run python -m chatbot.cli --help`
- Logging levels: set `LOG_LEVEL=DEBUG` temporarily when reproducing incidents.
- See `docs/MASTER_PROMPTS_HARDENING.md` for alignment prompts when coordinating hardening, QA, or launch work.
