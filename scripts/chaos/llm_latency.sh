#!/usr/bin/env bash
set -euo pipefail

# Injects latency into the upstream LLM endpoint using Toxiproxy.
# Requires toxiproxy-cli configured with a proxy that fronts the LLM service.

PROXY_NAME="${PROXY_NAME:-llm-upstream}"
LATENCY_MS="${LATENCY_MS:-3000}"
JITTER_MS="${JITTER_MS:-500}"
UPTIME_SECONDS="${UPTIME_SECONDS:-600}"

echo ":: Adding ${LATENCY_MS}ms latency (+/- ${JITTER_MS}) to ${PROXY_NAME}"
toxiproxy-cli t add "${PROXY_NAME}" -t latency -n llm-latency \
  -a latency="${LATENCY_MS}" -a jitter="${JITTER_MS}"

trap 'toxiproxy-cli t remove "${PROXY_NAME}" --toxic llm-latency' EXIT

for (( seconds = 0; seconds < UPTIME_SECONDS; seconds += 10 )); do
  echo ":: Chaos active... (${seconds}/${UPTIME_SECONDS}s)"
  sleep 10
done

echo ":: Removing latency toxic"
toxiproxy-cli t remove "${PROXY_NAME}" --toxic llm-latency
