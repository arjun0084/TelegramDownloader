#!/usr/bin/env bash
# Telegram Movie Downloader — one-command install / update wrapper.
#
# The image comes from Docker Hub, so there is NOTHING to build or clone.
#
# ONE-COMMAND INSTALL (Docker + compose plugin required):
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

# ---- 3. Go --------------------------------------------------------------
ACTION="${1:-up}"
case "$ACTION" in
  up|start)
    echo ">> Ensuring image is present, then starting..."
    docker compose up -d
    ;;
  update|upgrade|pull)
    echo ">> Pulling latest image from Docker Hub..."
    docker compose pull
    echo ">> Recreating container with the new image..."
    docker compose up -d
    ;;
  down|stop)
    echo ">> Stopping container..."
    docker compose down
    ;;
  restart)
    echo ">> Restarting container..."
    docker compose restart
    ;;
  logs)
    docker compose logs -f --tail=100
    ;;
  ps|status)
    docker compose ps
    ;;
  *)
    echo "Usage: $0 [up|update|down|restart|logs|status]"
    exit 1
    ;;
esac
