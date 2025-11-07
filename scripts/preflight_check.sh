#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/preflight_check.sh [namespace] [release] [values-file]

Defaults:
  namespace    xin-staging
  release      xin-platform
  values-file  deploy/helm/xin-platform/values-staging.yaml

Environment variables:
  EXTERNAL_SECRET_NAME   Secret name to verify when External Secrets are enabled (default: xin-orchestrator-secrets)
  CHECK_METRICS          When set to "true", run a curl probe against the metrics endpoint exposed inside the cluster
  METRICS_SERVICE_HOST   Service DNS name used for the optional metrics probe (default: <release>-orchestrator)
  METRICS_SERVICE_PORT   Port used for the optional metrics probe (default: 8000)
  METRICS_PATH           Path used for the optional metrics probe (default: /metrics)
  METRICS_TIMEOUT        Timeout (in seconds) for the optional metrics probe (default: 10)

This script renders the xin-platform chart, ensures the namespace exists,
and verifies that required secrets (when External Secrets are enabled) are present.
USAGE
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
CHART_DIR="${REPO_ROOT}/deploy/helm/xin-platform"

NAMESPACE=${1:-xin-staging}
RELEASE=${2:-xin-platform}
VALUES=${3:-${CHART_DIR}/values-staging.yaml}
EXTERNAL_SECRET_NAME=${EXTERNAL_SECRET_NAME:-xin-orchestrator-secrets}
CHECK_METRICS=${CHECK_METRICS:-false}
METRICS_SERVICE_HOST=${METRICS_SERVICE_HOST:-${RELEASE}-orchestrator}
METRICS_SERVICE_PORT=${METRICS_SERVICE_PORT:-8000}
METRICS_PATH=${METRICS_PATH:-/metrics}
METRICS_TIMEOUT=${METRICS_TIMEOUT:-10}

has_external_secrets_in_values() {
  local file=$1
  if [[ ! -f "${file}" ]]; then
    return 1
  fi
  awk '
    /^externalSecrets:/ {section=1; next}
    section && /^[^[:space:]]/ {exit 1}
    section && /^[[:space:]]*enabled:[[:space:]]*true/ {exit 0}
    {next}
    END {exit 1}
  ' "${file}" >/dev/null
}

echo "Preflight: namespace=${NAMESPACE}, release=${RELEASE}, values=${VALUES}"

if ! command -v helm >/dev/null 2>&1; then
  echo "helm binary is required but was not found in PATH" >&2
  exit 1
fi

rendered_template=$(mktemp)
trap 'rm -f "${rendered_template}"' EXIT

if ! helm template "${RELEASE}" "${CHART_DIR}" --values "${VALUES}" >"${rendered_template}"; then
  echo "helm template failed for release ${RELEASE} with values ${VALUES}" >&2
  exit 1
fi

KUBECTL_AVAILABLE=false
if command -v kubectl >/dev/null 2>&1; then
  KUBECTL_AVAILABLE=true
  if ! kubectl get ns "${NAMESPACE}" >/dev/null 2>&1; then
    echo "Namespace ${NAMESPACE} not found or inaccessible" >&2
    exit 1
  fi
else
  echo "kubectl not found; skipping namespace and cluster checks" >&2
fi

should_check_external_secret=false
if grep -Eq 'externalSecrets([[:space:]]|\.)+enabled:[[:space:]]*true' "${rendered_template}"; then
  should_check_external_secret=true
elif has_external_secrets_in_values "${CHART_DIR}/values-production.yaml"; then
  should_check_external_secret=true
fi

if [[ "${should_check_external_secret}" == "true" ]]; then
  if [[ "${KUBECTL_AVAILABLE}" == "false" ]]; then
    echo "External Secrets enabled but kubectl unavailable; cannot verify ${EXTERNAL_SECRET_NAME}" >&2
    exit 1
  fi
  if ! kubectl get secret "${EXTERNAL_SECRET_NAME}" -n "${NAMESPACE}" >/dev/null 2>&1; then
    echo "Expected secret ${EXTERNAL_SECRET_NAME} not found in namespace ${NAMESPACE}" >&2
    exit 1
  fi
  echo "Verified presence of secret ${EXTERNAL_SECRET_NAME} in ${NAMESPACE}"
else
  echo "External Secrets disabled for this release; skipping secret existence check"
fi

if [[ "${CHECK_METRICS}" == "true" ]]; then
  if [[ "${KUBECTL_AVAILABLE}" == "false" ]]; then
    echo "Cannot perform metrics probe without kubectl" >&2
    exit 1
  fi
  echo "Probing metrics endpoint http://${METRICS_SERVICE_HOST}:${METRICS_SERVICE_PORT}${METRICS_PATH}"
  METRICS_JOB="preflight-metrics-${RANDOM}"
  if ! kubectl run "${METRICS_JOB}" \
    --rm -i --restart=Never \
    --image=curlimages/curl:8.5.0 \
    --namespace "${NAMESPACE}" \
    --command -- sh -c "curl -sf --max-time ${METRICS_TIMEOUT} http://${METRICS_SERVICE_HOST}:${METRICS_SERVICE_PORT}${METRICS_PATH}" >/dev/null; then
    echo "Metrics probe failed for http://${METRICS_SERVICE_HOST}:${METRICS_SERVICE_PORT}${METRICS_PATH}" >&2
    exit 1
  fi
  echo "Metrics endpoint responded successfully"
fi

echo "Preflight checks passed"
