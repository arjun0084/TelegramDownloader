#!/usr/bin/env bash
# Build + run the Telegram downloader with plain `docker` (no compose needed).
# Run on the HOST. Edit MEDIA_HOST_DIR to your real USB path.

set -euo pipefail

cd "$(dirname "$0")"

# ---- EDIT ME: your real media mount path ----
MEDIA_HOST_DIR=/media/devmon/sda1-usb-Kingston_DataTra

# Add your Telegram user id to lock it down (0 = allow anyone private).
TG_ALLOWED_USER_ID=0

# load values from .env (export them into container env)
set -a; source .env; set +a

echo ">> Building image ..."
docker build -t tgdl:latest .

echo ">> Starting container (downloads -> $MEDIA_HOST_DIR) ..."
docker rm -f tgdl 2>/dev/null || true
docker run -d \
  --name tgdl \
  --restart unless-stopped \
  -v "$MEDIA_HOST_DIR":/downloads \
  -v tgdl_data:/data \
  -e TG_API_ID="$TG_API_ID" \
  -e TG_API_HASH="$TG_API_HASH" \
  -e TG_BOT_TOKEN="$TG_BOT_TOKEN" \
  -e TG_OUTPUT_DIR=/downloads \
  -e TG_ALLOWED_USER_ID="$TG_ALLOWED_USER_ID" \
  tgdl:latest

echo ">> Container started. Follow logs:  docker logs -f tgdl"