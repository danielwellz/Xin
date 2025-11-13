#!/usr/bin/env bash
set -euo pipefail

# Simulates a Redis outage by deleting/suspending pods in the target namespace.

NAMESPACE="${NAMESPACE:-xin-prod}"
STATEFULSET="${STATEFULSET:-redis}"
DISRUPTION_SECONDS="${DISRUPTION_SECONDS:-120}"

echo ":: Deleting Redis pods in ${NAMESPACE}/${STATEFULSET}"
kubectl -n "${NAMESPACE}" delete pod -l "app=${STATEFULSET}" --wait=false

echo ":: Waiting ${DISRUPTION_SECONDS}s before allowing statefulset to recover"
sleep "${DISRUPTION_SECONDS}"

echo ":: Forcing StatefulSet rollout"
kubectl -n "${NAMESPACE}" rollout status statefulset/"${STATEFULSET}"
