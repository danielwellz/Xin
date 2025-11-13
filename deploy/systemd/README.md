# Systemd Units

This directory contains hardened unit files for bare-metal installs on the Xin VPS
or other hosts where Docker/Kubernetes is unavailable. Each service reads a
dedicated environment file from `/opt/xin-chatbot/config/*.env`, runs inside the
project virtualenv, and only binds to localhost so Nginx can terminate TLS.

## Files

| Unit | Purpose | Health Check |
| --- | --- | --- |
| `xin-orchestrator.service` | FastAPI / gRPC API surface (`uvicorn`) | `http://127.0.0.1:${ORCHESTRATOR_PORT}/health` |
| `xin-channel-gateway.service` | Channel + webhook gateway | `http://127.0.0.1:${GATEWAY_PORT}/health` |
| `xin-ingestion-worker.service` | RAG ingestion / embeddings worker (ARQ) | `http://127.0.0.1:${INGEST_METRICS_PORT}/metrics` |
| `xin-automation-worker.service` | APScheduler-driven automation executor | `http://127.0.0.1:${OTEL_METRICS_PORT}/metrics` |

The shared helper `scripts/systemd/healthcheck.sh` blocks a start until the HTTP
endpoint responds, preventing Systemd from declaring a service “up” before it is
ready.

## Installation

```bash
sudo cp deploy/systemd/xin-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now xin-orchestrator xin-channel-gateway xin-ingestion-worker xin-automation-worker
```

Populate the environment files referenced inside each unit. Secrets **must not**
reside in git; load them from Vault or the `scripts/tls/bootstrap_certbot.sh`
workflow and write to `/opt/xin-chatbot/config/*.env`.

Example snippet (`/opt/xin-chatbot/config/orchestrator.env`):

```bash
ORCHESTRATOR_BIND=127.0.0.1
ORCHESTRATOR_PORT=8000
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=<redacted>
QDRANT_URL=http://127.0.0.1:6333
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
```

## TLS + Reverse Proxy

Systemd services only bind to loopback. Use Nginx (or Caddy) to terminate HTTPS,
enable HSTS, and forward to the local ports. The Certbot automation scripts in
`scripts/tls/` handle certificate issuance (`bootstrap_certbot.sh`) and renewals
(`renew_certificates.sh`), reloading Nginx once new material is written.
