#!/usr/bin/env bash
# Thin wrapper around `docker compose` for the Telegram downloader.
# The image comes from Docker Hub, so there is NOTHING to build/clone on the
# host — install, update, and day-to-day control are one command each.
#
# Usage:
#   ./run.sh            # install or update: pull image + start container
#   ./run.sh up         # same as above
#   ./run.sh update     # pull the latest image + recreate the container
#   ./run.sh down       # stop & remove container (image kept)
#   ./run.sh restart    # restart the container
#   ./run.sh logs       # follow container logs
#   ./run.sh status     # container status
#
# Needs: docker + docker compose plugin (or `docker-compose` v2).
# Secrets live in .env (copy from .env.example). Edit the media path inside
# docker-compose.yml to your real USB/downloads directory.

set -euo pipefail
cd "$(dirname "$0")"

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
