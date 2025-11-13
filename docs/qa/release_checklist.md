# Release Verification Checklist (Template)

| Field | Value |
| --- | --- |
| Release tag / commit |  |
| Date |  |
| QA Owner |  |

## 1. Automated Test Runs

| Suite | Command | Result | Artefact |
| --- | --- | --- | --- |
| Backend pytest | `poetry run pytest` | Pass / Fail | `logs/pytest-<date>.txt` |
| Backend coverage | `poetry run coverage xml` | ≥85 %? | `coverage.xml` |
| Frontend unit | `pnpm --prefix services/frontend test -- --coverage` | ≥80 %? | `services/frontend/coverage` |
| Frontend e2e | `pnpm --prefix services/frontend e2e -- --headless` | Pass / Fail | Cypress video path |
| Widget tests | `pnpm --prefix services/widget test` | Pass / Fail |  |
| Performance smoke | `k6 run tests/perf/orchestrator.js ...` | P95 < 1.5 s? | `perf-summary.json` |

Notes:

## 2. Migration Drill

- [ ] Pre-upgrade snapshot saved (`/tmp/pre-upgrade.dump`)
- [ ] `alembic upgrade head` logs attached
- [ ] Post-upgrade snapshot (`/tmp/post-upgrade.dump`)
- [ ] `alembic downgrade -1` + re-upgrade succeeded
- [ ] Diff file path: `docs/demos/perf/<date>-migration.diff`
- [ ] Key table counts matched (attach SQL output)

Notes:

## 3. Data Isolation

- [ ] Automated tests covering tenant isolation passed
- [ ] Manual UI check (Tenant A vs Tenant B) shows no leakage
- Evidence path(s):

## 4. Alert Validation

| Scenario | Script | Alert Fired? | Alert Resolved? | Evidence |
| --- | --- | --- | --- | --- |
| LLM latency | `scripts/chaos/llm_latency.sh` |  |  | Grafana PNG, Alert JSON |
| Redis outage | `scripts/chaos/redis_outage.sh` |  |  |  |
| Qdrant throttle | `scripts/chaos/qdrant_throttle.sh` |  |  |  |
| Channel spike | `scripts/chaos/channel_spike.sh` |  |  |  |

## 5. Manual Exploratory

- Operator console ✅/❌ — notes/issues:
- Widget ✅/❌ — notes/issues:
- Automation UI ✅/❌ — notes/issues:
- Mobile/RTL ✅/❌ — notes/issues:

List any new bugs (ID, severity, owner):

## 6. Coverage & Quality Gates

| Metric | Target | Actual | Pass? |
| --- | --- | --- | --- |
| Backend line coverage (critical pkgs) | ≥85 % |  |  |
| Frontend unit coverage | ≥80 % |  |  |
| Cypress smoke completion | 100 % |  |  |
| Alert validation | All alerts fired/resolved |  |  |
| Defects triaged | Sev1/Sev2 open? |  |  |

## 7. Sign-off

- [ ] All criteria met / waivers documented
- QA Lead signature:
- Platform Lead ack:
- Security Lead ack (if waivers):

Attach this document, artefact links, and bug tracker export to the release
record in `docs/ROADMAP.md#release-log`.
