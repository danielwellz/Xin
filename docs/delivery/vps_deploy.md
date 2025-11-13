# VPS Deployment Playbook (xinbot.ir)

This guide captures the exact steps required to deploy the latest Xin ChatBot build to the production VPS (`xinbot.ir`). It assumes the infrastructure baseline described in `docs/MASTER_PROMPTS_HARDENING.md` and the runbook’s SLO/ops guidance.

## 1. Environment Snapshot
- **Server**: Ubuntu 24.04 @ `87.107.105.19`, SSH user `xin` (sudo + docker group).
- **Repo & Config**: `/opt/xin-chatbot/src` (git), `/opt/xin-chatbot/config/compose.env`, `/opt/xin-chatbot/config/prod.env`.
- **Services**: Docker Compose stack (`xin_orchestrator`, `xin_channel_gateway`, `xin_ingestion_worker`, Postgres, Redis, Qdrant, MinIO).
- **Systemd**: `xin-chatbot.service` controls the compose stack (`sudo systemctl restart xin-chatbot`).
- **Reverse Proxy**: `/etc/nginx/sites-available/xin.conf` (HTTPS termination, `/` → orchestrator, `/webhooks/` → gateway).
- **Certificates**: Let’s Encrypt (`/etc/letsencrypt/live/xinbot.ir/`), renewed automatically via Certbot timer.
- **Health Checks**: `curl -sf https://xinbot.ir/health`, `curl -sf https://xinbot.ir/webhooks/health`.

## 2. Prerequisites
1. SSH access: `ssh -p 9011 xin@87.107.105.19`.
2. GitHub deploy key or credentials allowing `git fetch origin main`.
3. `ADMIN_TOKEN` (platform_admin JWT) if you need to seed demo tenants via `make demo`.
4. Ensure CI (`.github/workflows/ci.yml`) is green for at least 7 consecutive days (`make ci` locally for verification).

## 3. Deployment Steps
> All commands run on the VPS unless noted.

1. **Connect & prep**
   ```bash
   ssh -p 9011 xin@87.107.105.19
   cd /opt/xin-chatbot/src
   git fetch origin main
   git reset --hard origin/main
   ```
2. **Pull/Build containers**
   ```bash
   docker compose --env-file ../config/compose.env pull
   docker compose --env-file ../config/compose.env build --pull
   ```
3. **Restart via systemd (preferred)**
   ```bash
   sudo systemctl restart xin-chatbot
   sudo systemctl status xin-chatbot --no-pager
   ```
   > For emergency compose-level control: `docker compose --env-file ../config/compose.env up -d --remove-orphans`.

4. **Database migrations**
   ```bash
   docker compose exec orchestrator bash -lc "cd /app && /opt/venv/bin/alembic upgrade head"
   ```

5. **Frontend/widget assets**
   - Already bundled inside the repo; Docker build copies `services/frontend/dist` and `services/widget/dist`.
   - To serve new assets independently, ensure Nginx location blocks are updated (e.g., `/embed.js` proxied to the frontend container bound to `127.0.0.1:<port>`).

## 4. Verification Checklist
1. **Health endpoints**
   ```bash
   curl -sf http://127.0.0.1:8000/health && echo "Orchestrator OK"
   curl -sf http://127.0.0.1:8080/health && echo "Gateway OK"
   curl -sf https://xinbot.ir/health && echo "HTTPS OK"
   curl -sf https://xinbot.ir/webhooks/health && echo "Public webhooks OK"
   ```
2. **Logs**
   ```bash
   docker logs --tail=200 xin_orchestrator
   docker logs --tail=200 xin_channel_gateway
   docker logs --tail=200 xin_ingestion_worker
   ```
3. **Demo data (optional)**
   ```bash
   ADMIN_TOKEN=<platform_admin_jwt> make demo
   ```
   This provisions `Demo Tenant` + `Demo Web` channel and prints the latest embed snippet.

4. **Widget/Frontend smoke**
   - Access `https://xinbot.ir` (operator console) and ensure login + bilingual flows work.
   - Load `https://xinbot.ir/embed.js` snippet inside staging or `examples/widget-demo` to confirm handshake + telemetry.

5. **Monitoring**
   - Review Grafana dashboards (API latency, ingestion lag, automation queue depth).
   - Verify Alertmanager notifications are quiet after deploy.

## 5. Post-Deploy Tasks
1. Update `docs/ROADMAP.md#release-log` with the build hash, CI link, Grafana screenshots, and demo recording link.
2. Send the weekly status update using `docs/comms/status_template.md`.
3. Record any incidents or anomalies in `docs/demos/phase_walkthroughs.md` under the relevant phase.

## 6. Troubleshooting Quick Reference
- **Systemd failure**: `journalctl -u xin-chatbot -n 200 --no-pager`.
- **Cert issues**: `sudo certbot renew --dry-run`; ensure CDN points to the origin on 443.
- **Port binding**: All new services must bind to `127.0.0.1:<port>` and be proxied via Nginx (never expose raw ports).
- **Rollback**: `git reset --hard <previous-tag>` followed by steps in §3 and database rollback per `docs/MASTER_PROMPTS_HARDENING.md#prompt-5`.
