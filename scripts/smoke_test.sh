echo "Running health check against orchestrator"
echo "Running health check against channel gateway"
echo "Smoke tests passed for ${ENVIRONMENT}"
#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/smoke_test.sh [staging|production]
# Optional environment variables:
#  INGESTION_URL - if set, will POST a small JSON payload to this URL from inside the cluster
#  INGESTION_PAYLOAD - optional JSON payload (must be single-quoted when exported). Defaults to a small sample.
#  INGESTION_VERIFY_URL - optional URL to poll (GET) to verify ingestion processed; polled until HTTP 200 or timeout

ENVIRONMENT=${1:-staging}
if [[ "$ENVIRONMENT" == "production" ]]; then
  NAMESPACE="xin-prod"
else
  NAMESPACE="xin-staging"
fi

RELEASE_NAME="xin-platform"

IMAGE="curlimages/curl:8.5.0"
ROLLOUT_TIMEOUT=${ROLLOUT_TIMEOUT:-180s}
PROBE_TIMEOUT_SECONDS=${PROBE_TIMEOUT_SECONDS:-10}
PROBE_RETRIES=${PROBE_RETRIES:-3}
ENQUEUE_TIMEOUT=${ENQUEUE_TIMEOUT:-60}

echo "Using namespace=${NAMESPACE} release=${RELEASE_NAME}"

set +e
# find deployments belonging to this helm release (label injected by helm charts)
DEPLOYMENTS=$(kubectl get deployments -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${RELEASE_NAME}" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
set -e

if [[ -z "${DEPLOYMENTS// /}" ]]; then
  echo "No deployments found for release ${RELEASE_NAME} in namespace ${NAMESPACE}. Falling back to two known deployments."
  ORCHESTRATOR_DEPLOYMENT="${RELEASE_NAME}-${RELEASE_NAME}-orchestrator"
  GATEWAY_DEPLOYMENT="${RELEASE_NAME}-${RELEASE_NAME}-channel-gateway"
  DEPLOYMENTS="${ORCHESTRATOR_DEPLOYMENT}
${GATEWAY_DEPLOYMENT}"
fi

echo "Waiting for rollouts for deployments:\n${DEPLOYMENTS}"
for d in ${DEPLOYMENTS}; do
  echo "Waiting rollout for deployment/${d} (timeout=${ROLLOUT_TIMEOUT})"
  kubectl rollout status deployment/${d} -n ${NAMESPACE} --timeout=${ROLLOUT_TIMEOUT}
done

# Probe services: find services for this release and probe /health and /metrics on the first port
SERVICES=$(kubectl get svc -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${RELEASE_NAME}" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.ports[0].port}{"\n"}{end}')

if [[ -z "${SERVICES// /}" ]]; then
  echo "No services found for release ${RELEASE_NAME} in namespace ${NAMESPACE}. Trying to probe default service names."
  SERVICES="${RELEASE_NAME}-${RELEASE_NAME}-orchestrator 8000
${RELEASE_NAME}-${RELEASE_NAME}-channel-gateway 8080"
fi

probe_once() {
  local svc=$1
  local port=$2
  local path=$3
  local name="smoke-probe-$(echo ${svc} | tr '/.' '-')-$RANDOM"
  local cmd="curl -sf --max-time ${PROBE_TIMEOUT_SECONDS} http://${svc}:${port}${path}"
  echo "Probing http://${svc}:${port}${path}"
  kubectl run "${name}" \
    --rm -i --restart=Never \
    --image=${IMAGE} \
    --namespace "${NAMESPACE}" \
    --command -- sh -c "${cmd}" >/dev/null 2>&1
  return $?
}

for line in ${SERVICES}; do
  svc=$(echo ${line} | awk '{print $1}')
  port=$(echo ${line} | awk '{print $2}')
  for path in "/health" "/metrics"; do
    ok=1
    for i in $(seq 1 ${PROBE_RETRIES}); do
      if probe_once "${svc}" "${port}" "${path}"; then
        echo "OK: ${svc}:${port}${path}"
        ok=0
        break
      else
        echo "Attempt ${i}/${PROBE_RETRIES} failed for ${svc}:${port}${path}; retrying..."
        sleep 1
      fi
    done
    if [[ ${ok} -ne 0 ]]; then
      echo "ERROR: Probe failed for ${svc}:${port}${path} after ${PROBE_RETRIES} tries"
      exit 1
    fi
  done
done

echo "Service probes (/health and /metrics) passed for release ${RELEASE_NAME} in ${ENVIRONMENT}"

# Optional: enqueue a small ingestion job from inside the cluster if INGESTION_URL is provided
if [[ -n "${INGESTION_URL:-}" ]]; then
  echo "Enqueueing ingestion to ${INGESTION_URL} from inside the cluster"
  PAYLOAD=${INGESTION_PAYLOAD:-'{"title":"smoke-test","content":"hello from smoke_test"}'}
  NAME="smoke-enqueue-$RANDOM"
  set +e
  kubectl run "${NAME}" \
    --rm -i --restart=Never \
    --image=${IMAGE} \
    --namespace "${NAMESPACE}" \
    --command -- sh -c "curl -sS -f -X POST -H 'Content-Type: application/json' -d '${PAYLOAD}' ${INGESTION_URL}"
  rc=$?
  set -e
  if [[ ${rc} -ne 0 ]]; then
    echo "Failed to POST ingestion payload to ${INGESTION_URL}"
    exit 1
  fi
  echo "POST succeeded"

  if [[ -n "${INGESTION_VERIFY_URL:-}" ]]; then
    echo "Verifying ingestion by polling ${INGESTION_VERIFY_URL} for HTTP 200 (timeout ${ENQUEUE_TIMEOUT}s)"
    SECONDS_WAITED=0
    INTERVAL=2
    while [[ ${SECONDS_WAITED} -lt ${ENQUEUE_TIMEOUT} ]]; do
      if kubectl run verify-$(date +%s) --rm -i --restart=Never --image=${IMAGE} --namespace "${NAMESPACE}" --command -- sh -c "curl -sf --max-time 5 ${INGESTION_VERIFY_URL}" >/dev/null 2>&1; then
        echo "Ingestion verified (GET ${INGESTION_VERIFY_URL} returned 200)"
        break
      fi
      sleep ${INTERVAL}
      SECONDS_WAITED=$((SECONDS_WAITED + INTERVAL))
    done
    if [[ ${SECONDS_WAITED} -ge ${ENQUEUE_TIMEOUT} ]]; then
      echo "Timed out waiting for ingestion verification after ${ENQUEUE_TIMEOUT}s"
      exit 1
    fi
  fi
fi

echo "Smoke tests passed for ${ENVIRONMENT}"

