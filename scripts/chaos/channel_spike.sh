#!/usr/bin/env bash
set -euo pipefail

# Launches an additional burst of k6 users to simulate sudden channel spikes.

VUS="${VUS:-400}"
DURATION="${DURATION:-5m}"
WORKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

export GATEWAY_URL="${GATEWAY_URL:-https://gateway.xinbot.ir/webchat/webhook}"
export ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-https://api.xinbot.ir}"
export ADMIN_TOKEN="${ADMIN_TOKEN:?ADMIN_TOKEN is required}"
export WEBHOOK_SECRET="${WEBHOOK_SECRET:?WEBHOOK_SECRET is required}"

TMP_WORKLOAD="$(mktemp)"
yq -o=json "${WORKDIR}/tests/perf/workload_mix.yaml" > "${TMP_WORKLOAD}"

echo ":: Launching spike with ${VUS} VUs for ${DURATION}"
K6_VUS="${VUS}" K6_DURATION="${DURATION}" \
WORKLOAD_FILE="${TMP_WORKLOAD}" \
k6 run "${WORKDIR}/tests/perf/orchestrator.js"

rm -f "${TMP_WORKLOAD}"
