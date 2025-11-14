# Xin ChatBot Deploybook (Debian 12 + Docker Compose + Nginx)

This guide replaces the legacy runbooks and walks through provisioning the VPS at
`87.107.105.19`, deploying Xin ChatBot behind ArvanCloud, and keeping it current.
It describes three layers of configuration:

| Environment | Purpose | Env file |
| --- | --- | --- |
| Local dev | `poetry run uvicorn`, unit tests | `.env.local` |
| Local prod-like | Full stack via Docker Compose | `config/.env.docker` |
| VPS / production | `xinbot.ir` deployment | `/opt/xin-chatbot/config/.env.production` |

Set the `XIN_ENV_FILE` environment variable to point at the appropriate file when
running `docker compose`. Compose falls back to `config/.env.docker` when unset.

---

## 1. Server bootstrap (Debian 12)

```bash
# Create service user
sudo adduser --disabled-password --gecos "" xin
sudo usermod -aG sudo xin

# Harden SSH (optional but recommended)
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
sudo nano /etc/ssh/sshd_config   # Disable PasswordAuthentication, root login
sudo systemctl reload ssh

# Install base packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ufw ca-certificates gnupg \
    nginx python3-certbot-nginx

# Docker + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker xin
sudo systemctl enable docker

# Firewall (allow SSH + HTTP/S)
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw --force enable
```

Upload an SSH key for the `xin` user (`~/.ssh/authorized_keys`) and disable
password login to finish hardening.

---

## 2. Repository, config, and directory layout

```bash
sudo mkdir -p /opt/xin-chatbot/{src,config,volumes}
sudo chown -R xin:xin /opt/xin-chatbot

cd /opt/xin-chatbot/src
git clone https://github.com/<org>/xin-chatbot.git .
```

Create production env vars from the template:

```bash
cp config/examples/.env.production.example ../config/.env.production
chmod 600 ../config/.env.production
```

Fill in every `CHANGE_ME` value (Postgres, Redis, storage, LLM keys, channel
secrets, admin JWT secret, etc.). Keep this file off Git and back it up securely.

Export the path for convenience (add to `/home/xin/.profile` if desired):

```bash
export XIN_ENV_FILE=../config/.env.production
```

---

## 3. Docker Compose workflow

```bash
cd /opt/xin-chatbot/src
export XIN_ENV_FILE=${XIN_ENV_FILE:-../config/.env.production}

docker compose --env-file "$XIN_ENV_FILE" pull
docker compose --env-file "$XIN_ENV_FILE" build --pull
docker compose --env-file "$XIN_ENV_FILE" up -d --remove-orphans

# Apply the latest database migrations
docker compose --env-file "$XIN_ENV_FILE" exec orchestrator \
  bash -lc "cd /app && /opt/venv/bin/alembic upgrade head"
```

Check container health:

```bash
docker compose --env-file "$XIN_ENV_FILE" ps
docker compose --env-file "$XIN_ENV_FILE" logs -f orchestrator
docker compose --env-file "$XIN_ENV_FILE" logs -f channel_gateway
```

Named volumes (`postgres_data`, `redis_data`, `qdrant_data`, `minio_data`) live
under Docker’s default volume directory; snapshot these for backups.

---

## 4. Nginx + TLS

1. Copy `deploy/nginx/xin.conf` to `/etc/nginx/sites-available/xin.conf`. Verify
   the upstream ports (4173 frontend, 8000 API, 8080 gateway) match the Compose
   stack.

```bash
sudo cp /opt/xin-chatbot/src/deploy/nginx/xin.conf /etc/nginx/sites-available/xin.conf
sudo ln -s /etc/nginx/sites-available/xin.conf /etc/nginx/sites-enabled/xin.conf
sudo nginx -t && sudo systemctl reload nginx
```

2. Issue TLS certificates via Let’s Encrypt (replace the email):

```bash
sudo certbot --nginx -d xinbot.ir -d www.xinbot.ir --email ops@xinbot.ir --agree-tos
sudo systemctl status certbot.timer    # ensure renewals are scheduled
```

3. Health endpoints to verify (run from any host):

```bash
curl -sf https://xinbot.ir/health
curl -sf https://xinbot.ir/api/health
curl -sf https://xinbot.ir/webhooks/health
```

**ArvanCloud considerations**

- Configure the CDN to point to the VPS over HTTPS.
- Add page rules to bypass caching for `/api/*`, `/webhooks/*`, and `/health`.
- Preserve request headers (`X-Forwarded-For`, `X-Forwarded-Proto`) so the
  backend logs source IPs correctly.
- Disable compression/caching for webhook paths to avoid provider retries.

---

## 5. Redeploy procedure

```bash
cd /opt/xin-chatbot/src
git fetch origin main
git reset --hard origin/main

export XIN_ENV_FILE=../config/.env.production
docker compose --env-file "$XIN_ENV_FILE" pull
docker compose --env-file "$XIN_ENV_FILE" build --pull
docker compose --env-file "$XIN_ENV_FILE" up -d --remove-orphans
docker compose --env-file "$XIN_ENV_FILE" exec orchestrator \
  bash -lc "cd /app && /opt/venv/bin/alembic upgrade head"

sudo nginx -t && sudo systemctl reload nginx
```

Smoke-test the stack (`curl` commands above, sign in to the operator console,
send a test message through the CLI or widget). If something fails, roll back by
checking out the previous tag and re-running the same Compose commands.

---

## 6. Ops references

- **Systemd units** for orchestrator, gateway, and ingestion worker live under
  `deploy/systemd/`. Copy them to `/etc/systemd/system/` if you prefer systemd
  to supervise `uvicorn`/`arq` directly instead of Docker.
- **Backups**: dump Postgres via `docker compose exec postgres pg_dump ...`,
  mirror MinIO buckets with `mc mirror`, and archive `/opt/xin-chatbot/config`.
- **Observability**: each service exposes `/metrics`. Point Prometheus at the
  host ports or run an internal scrape job inside the Docker network.

Keep this Deploybook in sync with future infra changes. When in doubt, update
`config/examples/*.example`, regenerate the stack with the new env vars, then
document the exact commands here.
