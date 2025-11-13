#!/usr/bin/env bash
set -euo pipefail

NGINX_SERVICE="${NGINX_SERVICE:-nginx}"

echo ":: Running certbot renew"
sudo certbot renew --deploy-hook "systemctl reload ${NGINX_SERVICE}"
