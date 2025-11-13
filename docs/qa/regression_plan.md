# Regression Plan — Phase 4 GA

## 1. Scope & Feature Mapping

| Feature Area | Automated Coverage | Tool / Marker | Manual Notes |
| --- | --- | --- | --- |
| Admin API (tenant/channel CRUD, policies) | `tests/integration/admin/`, `tests/unit/chatbot/admin/` | `pytest -m "admin or integration"` | Postman smoke + onboarding UI walkthrough |
| Conversation flow (gateway → orchestrator) | `tests/load/locustfile.py`, `tests/perf/orchestrator.js` | Locust, k6 (`gateway_latency`, `orchestrator_latency`) | Validate multi-channel widget + WhatsApp webhooks |
| Ingestion (uploads, retries) | `tests/unit/chatbot/ingest/`, `tests/integration/ingestion/` | `pytest -m ingestion` | Manual ingest of PDF/HTML; ensure progress UI updates |
| Automation (rules, retries) | `tests/unit/chatbot/automation/`, `tests/integration/automation/` | `pytest -m automation` | Trigger CRM/webhook connectors and observe retries |
| Frontend console | `services/frontend` unit tests + Cypress e2e (`pnpm --prefix services/frontend e2e -- --headless`) | `@smoke` specs | Exploratory sweep for new tenants/channels, bilingual UI |
| Widget | `services/widget` unit tests, manual embed in `examples/widget-demo` | `pnpm --prefix services/widget test` | Validate offline banner, nonce/signature |
| Observability/alerts | Chaos scripts + alert smoke | See §5 | Confirm Alertmanager Slack/webhook notifications |
| Data migrations | Snapshot diff/rollback | See §3 | Use staging copy; record checksum diffs |

## 2. Test Execution Matrix

```bash
poetry run pytest --maxfail=1 --disable-warnings -m "not perf"
poetry run coverage xml
pnpm --prefix services/frontend install
pnpm --prefix services/frontend test -- --coverage
pnpm --prefix services/frontend e2e -- --headless --config tests/cypress.config.ts
pnpm --prefix services/widget test
```

Targets:
- Backend critical packages ≥85 % line coverage (verify in `coverage.xml`).
- Frontend unit tests ≥80 % (Jest output) and Cypress smoke covering the golden
  onboarding/chat flow (videos saved under `services/frontend/cypress/videos/`).

Tagging guidance:
- Use `@pytest.mark.admin`, `@pytest.mark.ingestion`, `@pytest.mark.automation`
  so subsets can be run per area.
- Cypress spec naming: `admin-onboarding.smoke.cy.ts`, `conversation-flow.smoke.cy.ts`.

## 3. Migration Integrity Drill

1. Snapshot staging database:
   ```bash
   pg_dump -Fc "$STAGING_DATABASE_URL" > /tmp/pre-upgrade.dump
   ```
2. Run migrations forward/back:
   ```bash
   TEST_DATABASE_URL=$STAGING_DATABASE_URL poetry run alembic upgrade head
   pg_dump -Fc "$STAGING_DATABASE_URL" > /tmp/post-upgrade.dump
   TEST_DATABASE_URL=$STAGING_DATABASE_URL poetry run alembic downgrade -1
   poetry run alembic upgrade head
   ```
3. Diff schema/data (ignoring sequences):
   ```bash
   pg_restore -f /tmp/pre.sql /tmp/pre-upgrade.dump
   pg_restore -f /tmp/post.sql /tmp/post-upgrade.dump
   diff -u <(grep -v 'SELECT pg_catalog.setval' /tmp/pre.sql) \
         <(grep -v 'SELECT pg_catalog.setval' /tmp/post.sql) > docs/demos/perf/$(date +%Y%m%d)-migration.diff
   ```
4. Validate key tables counts match:
   ```bash
   psql "$STAGING_DATABASE_URL" -c "SELECT count(*) FROM conversations;"
   ```
5. Attach the diff and command logs to the release checklist. Downtime must be
   zero; any data drift triggers a blocker bug.

## 4. Data Isolation Verification

Seed two tenants via API; store their JWTs separately.

```bash
TENANT_A=$(curl .../admin/tenants)
TENANT_B=$(curl .../admin/tenants)
```

Automated test `tests/integration/admin/test_tenant_isolation.py` should assert:
- Tenant A cannot fetch Tenant B channels.
- Widget embed for Tenant A does not accept Tenant B nonce/signature.

Manual spot check: run `scripts/demo_onboarding.py` twice with different base
URLs, ensuring cross-tenant data never appears in the UI.

## 5. Alert & Observability Validation

Use `scripts/chaos/`:
- `llm_latency.sh` → expect `HighLatencyLLM` in Alertmanager, Tempo traces
  showing fallback model.
- `redis_outage.sh` → `GatewayHealthCheckFailed` + automation queue depth alert.
- `qdrant_throttle.sh` → `IngestionLagHigh`.
- `channel_spike.sh` → HPAs scale (capture `kubectl describe hpa`).

For each run:
1. Start `k6 run tests/perf/orchestrator.js --vus 200 --duration 10m`.
2. Execute chaos script.
3. Capture Grafana screenshots + Alertmanager JSON payloads; store under
   `docs/demos/perf/<date>/`.
4. Note recovery time and whether alerts resolved automatically.

## 6. Manual Exploratory Checklist

- Operator console: login, create/edit tenant, add channel, rotate secrets.
- Automation UI: create rule, pause/resume, inspect job history.
- Widget: embed in `examples/widget-demo`, test offline mode + RTL text.
- Mobile/responsive breakpoints (Chrome device simulation).
- Regression areas reported in the last release (list open bugs + verify status).

Document findings (severity, owner, status) in the release checklist.

## 7. Deliverables

- Automated test outputs: `coverage.xml`, Jest coverage report, Cypress videos,
  `k6` summary JSON, `locust` CSV (optional).
- Migration diff log + rollback transcript.
- Alert validation evidence (Grafana PNGs, Alertmanager JSON).
- Bug tracker export (CSV or screenshot) with severity/owners.
- Completed `docs/qa/release_checklist.md` referencing all artefacts.
