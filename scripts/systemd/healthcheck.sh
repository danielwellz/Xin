#!/usr/bin/env bash
set -euo pipefail

URL=""
MAX_WAIT=60
INTERVAL=5
NAME="xin-service"
INSECURE=0

usage() {
  echo "Usage: $0 --url <https://...> [--max-wait 120] [--interval 5] [--name xin] [--insecure]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      URL="$2"
      shift 2
      ;;
    --max-wait)
      MAX_WAIT="$2"
      shift 2
      ;;
    --interval)
      INTERVAL="$2"
      shift 2
      ;;
    --name)
      NAME="$2"
      shift 2
      ;;
    --insecure)
      INSECURE=1
      shift
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$URL" ]]; then
  usage
  exit 1
fi

deadline=$((SECONDS + MAX_WAIT))
curl_flags=(-fsS "$URL")
if [[ $INSECURE -eq 1 ]]; then
  curl_flags=(-k "${curl_flags[@]}")
fi

while true; do
  if curl "${curl_flags[@]}" >/dev/null 2>&1; then
    echo ":: $NAME healthy at $URL"
    exit 0
  fi
  if (( SECONDS >= deadline )); then
    echo ":: $NAME failed health check for $URL within ${MAX_WAIT}s" >&2
    exit 1
  fi
  sleep "$INTERVAL"
done
