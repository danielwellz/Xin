# Xin ChatBot Production Deployment (xinbot.ir)

This document is the canonical runbook for deploying and operating Xin ChatBot on the
production VPS (`xinbot.ir`). The guidance assumes the infrastructure described in
`AGENTS.md` and mirrors the live topology: Docker Compose stack managed by
`systemd`, TLS terminated by Nginx, and a CDN in front of the VPS.

---

## 1. Environment Snapshot

- **Host:** Ubuntu 24.04 @ `87.107.105.19`
- **SSH:** `ssh -p 9011 xin@87.107.105.19`
- **Repo:** `/opt/xin-chatbot/src` (git working tree)
- **Config:** `/opt/xin-chatbot/config`
  - `compose.env` — infra-level env vars (DB creds, storage, etc.)
 - `prod.env` — application secrets consumed by the containers
- **Env indirection:** `../config/compose.env` must define `XIN_COMPOSE_ENV_FILE=../config/prod.env`
  so Docker Compose loads runtime secrets via `env_file`.
- **Volumes:** `/opt/xin-chatbot/volumes/{postgres,redis,qdrant,minio,...}`
- **Systemd unit:** `/etc/systemd/system/xin-chatbot.service`
- **Reverse proxy:** `/etc/nginx/sites-available/xin.conf` (symlinked in `sites-enabled`)
  - `/` → operator console (`frontend` container @ `127.0.0.1:4173`)
  - `/api/` → orchestrator (`127.0.0.1:8000`)
  - `/webhooks/` → channel gateway (`127.0.0.1:8080`)
- **Certificates:** Let’s Encrypt (`/etc/letsencrypt/live/xinbot.ir/*`) renewed via `certbot.timer`

---

## 2. Prerequisites

1. SSH access as `xin` and membership in the `docker` group.
2. Up-to-date `compose.env` and `prod.env` under `/opt/xin-chatbot/config`.
3. Git remote pointing to the correct repository (main branch is the deployment target).
4. `sudo` password for actions that touch Nginx, certbot, or systemd.
5. Optional: `ADMIN_TOKEN` with `platform_admin` scope for smoke tests or seeding demo data. Generate one directly on the host:

   ```bash
   cd /opt/xin-chatbot/src
   poetry run python - <<'PY'
   from chatbot.admin.auth import JWTService
   from chatbot.core.config import AppSettings
   settings = AppSettings.load()
   svc = JWTService(
       secret=settings.admin_auth.jwt_secret,
       issuer=settings.admin_auth.issuer,
       audience=settings.admin_auth.audience,
       ttl_seconds=settings.admin_auth.access_token_ttl_minutes * 60,
   )
   print(svc.issue_token(subject="bootstrap-ops", roles=["platform_admin"]))
   PY
   export ADMIN_TOKEN=<printed_jwt>
   ```

---

## 3. Routine Redeploy (Main → Production)

> All commands run on the VPS unless noted. Substitute the branch/tag as needed.

```bash
ssh -p 9011 xin@87.107.105.19
cd /opt/xin-chatbot/src
git fetch origin main
git reset --hard origin/main
```

Build and stage container images using the shared env file:

```bash
docker compose --env-file ../config/compose.env pull
docker compose --env-file ../config/compose.env build --pull
docker compose --env-file ../config/compose.env up -d --remove-orphans

# Refresh the operator console bundle (frontend container serves https://xinbot.ir/)
docker compose --env-file ../config/compose.env build frontend
docker compose --env-file ../config/compose.env up -d frontend

# Reload nginx so / proxies the updated bundle; purge CDN cache via the ParsVDS panel
sudo nginx -t && sudo systemctl reload nginx
# (CDN) https://panel.parsvds.com/cdn/cache/purge?domain=xinbot.ir
```

Apply database migrations inside the orchestrator container (Alembic):

```bash
docker compose --env-file ../config/compose.env exec orchestrator \
  bash -lc "cd /app && /opt/venv/bin/alembic upgrade head"
```

Restart the managed stack via systemd (preferred for parity with boot-time behavior):

```bash
sudo systemctl restart xin-chatbot
sudo systemctl status xin-chatbot --no-pager
```

If any container fails, inspect with `docker compose --env-file ../config/compose.env ps` and
review individual logs (see §5).

---

## 4. Health Checks & Verification

### Internal (origin-only)

```bash
curl -sf http://127.0.0.1:8000/health && echo "Orchestrator OK"
curl -sf http://127.0.0.1:8080/health && echo "Gateway OK"
```

### External (through CDN + Nginx)

```bash
curl -sf https://xinbot.ir/health && echo "HTTPS OK"
curl -sf https://xinbot.ir/webhooks/health && echo "Webhook OK"
curl -sf https://xinbot.ir | grep -qi "<title" && echo "Console OK"
```

After the console HTML check, mint a fresh `platform_admin` token, sign in at `https://xinbot.ir`, and verify the Tenants + Channels views render live data.

If an external check fails but the internal one passes, investigate CDN configuration,
certificate validity (`sudo certbot renew --dry-run`), and the Nginx site file.

---

## 5. Logs & Troubleshooting

| Component | Command |
| --- | --- |
| Systemd unit | `sudo journalctl -u xin-chatbot -n 200 --no-pager` |
| Orchestrator | `docker logs -f xin_orchestrator` |
| Channel gateway | `docker logs -f xin_channel_gateway` |
| Ingestion worker | `docker logs -f xin_ingestion_worker` |
| Nginx | `sudo tail -f /var/log/nginx/{access,error}.log` |

Common issues:

- **DB/Redis unavailable:** confirm containers are healthy (`docker compose ... ps`) and
  volumes under `/opt/xin-chatbot/volumes` are mounted. Restart individual services with
  `docker compose --env-file ../config/compose.env restart <service>`.
- **MinIO credentials mismatch:** ensure `STORAGE_*` values in `prod.env` align with the MinIO
  root credentials. Rotate secrets via the MinIO console at `127.0.0.1:9001`.
- **Webhook failures:** check `xin_channel_gateway` logs for HMAC or provider-specific errors.
  All webhook URLs must be `https://xinbot.ir/webhooks/<channel>`.
- **Nginx reload:** after editing `/etc/nginx/sites-available/xin.conf`, run
  `sudo nginx -t && sudo systemctl reload nginx`.

---

## 6. Backups & Data Safety

- **Postgres:** `/opt/xin-chatbot/scripts/backup_postgres.sh` produces compressed dumps under
  `/opt/xin-chatbot/backup/postgres/`. Schedule via `cron` or a systemd timer (see
  `scripts/systemd/` for templates). Restores use `psql` inside the postgres container.
- **MinIO:** mirror buckets with the MinIO client (`mc mirror minio/brand-knowledge /opt/xin-chatbot/backup/minio/`).
- **Config files:** version control + off-box copies of `compose.env` and `prod.env`.
- **Disaster recovery:** keep the latest Alembic migration ID and backup timestamps recorded in
  `docs/ROADMAP.md#release-log`.

---

## 7. Webhook Registration Cheat Sheet

| Channel | Public URL | Notes |
| --- | --- | --- |
| Telegram | `https://xinbot.ir/webhooks/telegram` | Use `setWebhook` with secret token; retries handled by Telegram. |
| Instagram | `https://xinbot.ir/webhooks/instagram` | Configure in Meta App dashboard; verify token stored in `prod.env`. |
| WhatsApp | `https://xinbot.ir/webhooks/whatsapp` | Meta Cloud API setup; ensure `hub.challenge` handshake succeeds (gateway logs). |
| Web Chat | `https://xinbot.ir/webhooks/web` (or `/webhooks/webchat`) | Used by widget + custom SDKs. |

- Store channel secrets via the admin API (`POST /admin/channels`) and keep rotated copies in Vault.
- Re-register webhooks after changing CDN/Nginx certificates or if providers disable the endpoint.

---

## 8. TLS, CDN, and Certificates

- CDN (parsvds panel) fronts `xinbot.ir` and connects to the origin over HTTPS:443. Keep HTTPS
  enabled end-to-end and ensure the CDN trusts Let’s Encrypt.
- Certificates live under `/etc/letsencrypt/live/xinbot.ir/`. Renewal is automated by `certbot`
  (`sudo systemctl list-timers | rg certbot`). Manual dry run:

  ```bash
  sudo certbot renew --dry-run
  ```

- After renewal, reload Nginx: `sudo systemctl reload nginx`.
- Any new HTTP service must bind to `127.0.0.1:<port>` inside Docker and be proxied through
  `xin.conf` (add a `location /app/ { proxy_pass http://127.0.0.1:<port>/; ... }` block).

---

## 9. Dev ↔ Prod Parity

- **Local stack:** `docker compose -f docker-compose.yml -f deploy/observability/docker-compose.yml --env-file deploy/compose/.env.dev up`.
- **Backend:** `poetry run uvicorn chatbot.adapters.orchestrator.app:create_app --factory --reload`.
- **Frontend:** defaults to `window.location.origin`; override via `.env` (`VITE_API_BASE_URL=http://localhost:8000`)
  when running `pnpm dev`.
- **Environment files:** never commit `prod.env`/`compose.env`. Use `.env` locally and `python-dotenv`
  already loads it for CLI tooling.

Keep the local environment aligned with production schemas, run `poetry run pytest` and
`make format` before every release, and document each deployment in `docs/ROADMAP.md#release-log`.

---

## 10. Quick Reference

```bash
# SSH + deploy
ssh -p 9011 xin@87.107.105.19
cd /opt/xin-chatbot/src
git fetch origin main && git reset --hard origin/main
docker compose --env-file ../config/compose.env pull
docker compose --env-file ../config/compose.env build --pull
docker compose --env-file ../config/compose.env up -d --remove-orphans
docker compose --env-file ../config/compose.env exec orchestrator bash -lc "cd /app && /opt/venv/bin/alembic upgrade head"
sudo systemctl restart xin-chatbot

# Health
curl -sf https://xinbot.ir/health
curl -sf https://xinbot.ir/webhooks/health
```

Store this runbook alongside release notes so every deploy follows the same, auditable steps.
