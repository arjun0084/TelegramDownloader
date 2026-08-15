#!/usr/bin/env bash
# Telegram Movie Downloader — one-command install / update wrapper.
#
# The image comes from Docker Hub, so there is NOTHING to build or clone.
#
# ONE-COMMAND INSTALL (Docker required):
#   curl -fsSL -o run.sh https://raw.githubusercontent.com/arjun0084/TelegramDownloader/main/run.sh && bash run.sh
#
#   First run: it downloads docker-compose.yml + .env.example, creates .env,
#   and tells you to fill in your secrets. Then run `./run.sh` again.
#
# Usage:
#   ./run.sh            # install/update: pull image + start container
#   ./run.sh up         # same as above
#   ./run.sh update     # pull latest image + recreate the container
#   ./run.sh down       # stop & remove container (image kept)
#   ./run.sh restart    # restart the container
#   ./run.sh logs       # follow container logs
#   ./run.sh status     # container status

set -euo pipefail

RAW_BASE="https://raw.githubusercontent.com/arjun0084/TelegramDownloader/main"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd || pwd)"
cd "$SCRIPT_DIR"

# ---- 0. Docker must be installed ----------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install it first: https://docs.docker.com/engine/install/" >&2
  exit 1
fi

# ---- 1. Self-bootstrap: fetch companion files if missing ----------------
# (needs the GitHub repo to be Public — raw URLs don't work with a token)
if [[ ! -f docker-compose.yml || ! -f .env.example ]]; then
  echo ">> First run detected — fetching docker-compose.yml and .env.example from GitHub..."
  [[ -f docker-compose.yml ]] || curl -fsSL -o docker-compose.yml "$RAW_BASE/docker-compose.yml"
  [[ -f .env.example ]]       || curl -fsSL -o .env.example "$RAW_BASE/.env.example"
  echo ">> Fetched."
fi

# ---- 2. Create .env from the template on first run ----------------------
if [[ ! -f .env ]]; then
  cp .env.example .env
  cat <<'EOF'

======================================================================
  .env created from the template. Fill in your secrets, then run
  ./run.sh again:

    nano .env
       1) TG_API_ID / TG_API_HASH / TG_BOT_TOKEN   (from my.telegram.org
          and @BotFather)
       2) MEDIA_HOST_DIR = full path to YOUR downloads folder

======================================================================
EOF
  exit 0
fi

# Source .env to get variables
set -a
# shellcheck disable=SC1091
source .env
set +a

# Defaults if not set
: "${TG_OUTPUT_DIR:=/downloads}"
: "${TG_MAX_PARALLEL:=2}"

# Container name
CONTAINER_NAME="tgdl"

# Function to run the container
run_container() {
  echo ">> Starting container $CONTAINER_NAME..."
  docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -v "$MEDIA_HOST_DIR:$TG_OUTPUT_DIR" \
    -v tgdl_data:/data \
    -e TG_API_ID \
    -e TG_API_HASH \
    -e TG_BOT_TOKEN \
    -e TG_OUTPUT_DIR \
    -e TG_ALLOWED_USER_ID \
    -e TG_MAX_PARALLEL \
    arjun0084/telegram-downloader:latest
}

# ---- 3. Go --------------------------------------------------------------
ACTION="${1:-up}"
case "$ACTION" in
  up|start)
    echo ">> Ensuring image is present, then starting..."
    docker pull arjun0084/telegram-downloader:latest
    # Remove existing container if any
    if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
      echo ">> Removing existing container..."
      docker rm -f "$CONTAINER_NAME" >/dev/null
    fi
    run_container
    ;;
  update|upgrade|pull)
    echo ">> Pulling latest image from Docker Hub..."
    docker pull arjun0084/telegram-downloader:latest
    echo ">> Recreating container with the new image..."
    if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
      docker rm -f "$CONTAINER_NAME" >/dev/null
    fi
    run_container
    ;;
  down|stop)
    echo ">> Stopping container..."
    if docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
      docker stop "$CONTAINER_NAME"
    fi
    if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
      docker rm "$CONTAINER_NAME"
    fi
    ;;
  restart)
    echo ">> Restarting container..."
    if docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
      docker restart "$CONTAINER_NAME"
    else
      echo ">> Container not running, starting..."
      docker pull arjun0084/telegram-downloader:latest
      run_container
    fi
    ;;
  logs)
    if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
      echo ">> Container $CONTAINER_NAME is not running." >&2
      exit 1
    fi
    docker logs -f --tail=100 "$CONTAINER_NAME"
    ;;
  ps|status)
    echo ">> Container status:"
    docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
    ;;
  *)
    echo "Usage: $0 [up|update|down|restart|logs|status]"
    exit 1
    ;;
esac