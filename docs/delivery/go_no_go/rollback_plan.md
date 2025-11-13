# Rollback & Contingency Plan

_Release:_  
_Prepared by:_  
_Last updated:_

## 1. Trigger Criteria

- P1/P0 incidents impacting ≥20 % of tenants for >15 minutes.
- Database corruption detected during smoke tests.
- Alertmanager `ApiErrorBudgetBurn` + `GatewayHealthCheckFailed` sustained for >10 minutes post-deploy.
- Security incident requiring credential revocation.

## 2. Rollback Decision Flow

1. Delivery Manager convenes war room; SRE validates symptom.
2. QA confirms reproduction; Platform lead assesses blast radius.
3. If rollback approved, follow sections below and document in incident log.

## 3. Application Rollback Steps

### 3.1 Kubernetes (Staging/Prod)
```bash
cd /opt/xin-chatbot/src
git fetch origin
git checkout <previous-tag>
kubectl apply -k deploy/overlays/prod
kubectl rollout status deploy/xin-xin-platform-orchestrator
kubectl rollout status deploy/xin-xin-platform-channel-gateway
```
Verify:
- `kubectl get pods -n xin-prod` shows previous image tags.
- `curl https://api.xinbot.ir/health` returns 200.

### 3.2 Docker Compose (VPS)
```bash
ssh xin@87.107.105.19
cd /opt/xin-chatbot/src
git checkout <previous-tag>
docker compose --env-file ../config/compose.env pull
sudo systemctl restart xin-chatbot
```
Verify with health checks and Grafana dashboards.

## 4. Database Rollback / Restore

1. Stop writes (put orchestrator in maintenance mode via feature flag `maintenance_mode=true`).
2. Restore Postgres snapshot:
   ```bash
   export PGPASSWORD=<secret>
   pg_restore --clean --if-exists -h localhost -U chatbot -d chatbot /opt/backups/xin-backup-<timestamp>.dump
   ```
3. Restore Qdrant snapshot:
   ```bash
   curl -X POST http://localhost:6333/snapshots/upload -F 'snapshot=@/opt/backups/qdrant.snap'
   ```
4. Restore object storage:
   ```bash
   aws --endpoint-url http://minio:9000 s3 sync /opt/backups/object-storage s3://brand-knowledge --delete
   ```
5. Run `alembic upgrade head` to ensure schema alignment.
6. Re-enable orchestrator and run smoketests.

## 5. Feature Flags / Contingencies

| Flag | Purpose | Location | Action |
| --- | --- | --- | --- |
| `maintenance_mode` | Disable public APIs | Admin feature flag service | Flip to `true` to halt traffic |
| `llm_provider` override | Switch to fallback LLM | Admin policies | Set to `fallback` to reduce upstream dependency |
| `automation_enabled` | Pause automation worker per tenant | Admin API `/admin/automation/rules/{id}/pause` | Pause noisy tenants before rollback |

## 6. Verification Post-Rollback

- Run `poetry run pytest -m smoke` and `k6 run tests/perf/orchestrator.js --vus 50 --duration 5m`.
- Confirm dashboards show pre-release baselines.
- Validate no data loss by comparing conversation counts pre/post rollback.
- QA signs off before re-opening traffic.

## 7. Communication

- Update status page (copy template from `docs/delivery/comms/status_page.md`).
- Notify stakeholders via email/slack (see comms package).
- Document in incident write-up and link to rollback logs.
