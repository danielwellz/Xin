#!/usr/bin/env bash
set -euo pipefail

DOMAIN=""
EMAIL=""
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"
CERT_DIR="${CERT_DIR:-/etc/letsencrypt/live}"
TARGET_CERT_DIR="${TARGET_CERT_DIR:-/opt/xin-chatbot/config/tls}"
EXTRA_DOMAINS=()

usage() {
  cat <<USAGE
Bootstrap Let's Encrypt certs for Xin ChatBot.

Usage: $0 --domain xinbot.ir --email sre@xinbot.ir [--extra chat.xinbot.ir]...
Environment:
  NGINX_SERVICE   systemd unit to reload after issuance (default: nginx)
  TARGET_CERT_DIR directory where cert/key symlinks are created (default: /opt/xin-chatbot/config/tls)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --email)
      EMAIL="$2"
      shift 2
      ;;
    --extra)
      EXTRA_DOMAINS+=("$2")
      shift 2
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  usage
  exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
  echo ":: Installing certbot"
  sudo apt-get update
  sudo apt-get install -y certbot
fi

DOMAINS=(-d "$DOMAIN" -d "www.$DOMAIN")
for extra in "${EXTRA_DOMAINS[@]}"; do
  DOMAINS+=(-d "$extra")
done

echo ":: Requesting certificates for ${DOMAINS[*]}"
sudo certbot certonly --standalone --preferred-challenges http \
  --agree-tos --non-interactive \
  -m "$EMAIL" "${DOMAINS[@]}"

sudo systemctl enable --now certbot.timer

LIVE_PATH="$CERT_DIR/$DOMAIN"
mkdir -p "$TARGET_CERT_DIR"
sudo ln -sf "$LIVE_PATH/fullchain.pem" "$TARGET_CERT_DIR/fullchain.pem"
sudo ln -sf "$LIVE_PATH/privkey.pem" "$TARGET_CERT_DIR/privkey.pem"

echo ":: Certificates linked under $TARGET_CERT_DIR"
echo ":: Reloading $NGINX_SERVICE"
sudo systemctl reload "$NGINX_SERVICE"
