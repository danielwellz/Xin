#!/usr/bin/env bash
set -euo pipefail

# Applies temporary network shaping to the Qdrant deployment to simulate degraded IO.

NAMESPACE="${NAMESPACE:-xin-prod}"
DEPLOYMENT="${DEPLOYMENT:-qdrant}"
LATENCY_MS="${LATENCY_MS:-800}"
LOSS_PERCENT="${LOSS_PERCENT:-5}"
DURATION_SECONDS="${DURATION_SECONDS:-300}"

PODS=$(kubectl -n "${NAMESPACE}" get pods -l app="${DEPLOYMENT}" -o jsonpath='{.items[*].metadata.name}')

for POD in ${PODS}; do
  echo ":: Applying tc rules to ${POD}"
  kubectl -n "${NAMESPACE}" exec "${POD}" -- tc qdisc add dev eth0 root netem delay "${LATENCY_MS}"ms loss "${LOSS_PERCENT}"%
done

sleep "${DURATION_SECONDS}"

for POD in ${PODS}; do
  echo ":: Clearing tc rules on ${POD}"
  kubectl -n "${NAMESPACE}" exec "${POD}" -- tc qdisc del dev eth0 root || true
done
