#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT=${1:-staging}
if [[ "$ENVIRONMENT" == "production" ]]; then
  NAMESPACE="xin-prod"
else
  NAMESPACE="xin-staging"
fi

RELEASE_NAME="xin-platform"
ORCHESTRATOR_DEPLOYMENT="${RELEASE_NAME}-${RELEASE_NAME}-orchestrator"
GATEWAY_DEPLOYMENT="${RELEASE_NAME}-${RELEASE_NAME}-channel-gateway"
ORCHESTRATOR_SERVICE="$ORCHESTRATOR_DEPLOYMENT"
GATEWAY_SERVICE="$GATEWAY_DEPLOYMENT"

kubectl rollout status deployment/${ORCHESTRATOR_DEPLOYMENT} -n ${NAMESPACE} --timeout=180s
kubectl rollout status deployment/${GATEWAY_DEPLOYMENT} -n ${NAMESPACE} --timeout=180s

echo "Running health check against orchestrator"
kubectl run smoke-probe-orchestrator \
  --rm -i --restart=Never \
  --image=curlimages/curl:8.5.0 \
  --namespace ${NAMESPACE} \
  --command -- sh -c "curl -sf http://${ORCHESTRATOR_SERVICE}:8000/health" >/dev/null

echo "Running health check against channel gateway"
kubectl run smoke-probe-gateway \
  --rm -i --restart=Never \
  --image=curlimages/curl:8.5.0 \
  --namespace ${NAMESPACE} \
  --command -- sh -c "curl -sf http://${GATEWAY_SERVICE}:8080/health" >/dev/null

echo "Smoke tests passed for ${ENVIRONMENT}"
