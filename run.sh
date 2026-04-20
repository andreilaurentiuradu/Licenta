#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
STACK="sportanalytics"

usage() {
  echo "Usage: $0 {build|start|stop|restart|status|logs [service]}"
  echo ""
  echo "  build            Build backend + frontend Docker images"
  echo "  start            Init swarm + deploy stack"
  echo "  stop             Remove the stack"
  echo "  restart          stop → build → start"
  echo "  status           Show running services"
  echo "  logs [service]   Tail logs (keycloak | backend | frontend)"
  exit 1
}

build_images() {
  echo "[build] Building backend image..."
  docker build -t sportanalytics-backend:latest "$ROOT/backend"

  echo "[build] Building frontend image..."
  docker build -t sportanalytics-frontend:latest "$ROOT/frontend"

  echo "[build] Done."
}

swarm_init() {
  if ! docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q active; then
    echo "[swarm] Initialising Docker Swarm..."
    docker swarm init
  else
    echo "[swarm] Already active."
  fi
}

stack_deploy() {
  echo "[deploy] Deploying stack '$STACK'..."
  cd "$ROOT"
  docker stack deploy -c docker-compose.yml "$STACK"

  echo ""
  echo "  Services:"
  echo "    Keycloak  → http://localhost:8080"
  echo "    Backend   → http://localhost:5000"
  echo "    Frontend  → http://localhost:3000"
  echo ""
  echo "  Use './run.sh logs keycloak' to follow Keycloak startup."
}

stack_stop() {
  echo "[stop] Removing stack '$STACK'..."
  docker stack rm "$STACK"
}

CMD="${1:-}"
case "$CMD" in
  build)
    build_images
    ;;
  start)
    swarm_init
    stack_deploy
    ;;
  stop)
    stack_stop
    ;;
  restart)
    stack_stop
    sleep 5
    build_images
    swarm_init
    stack_deploy
    ;;
  status)
    docker service ls
    ;;
  logs)
    SERVICE="${2:-keycloak}"
    docker service logs "${STACK}_${SERVICE}" -f
    ;;
  *)
    usage
    ;;
esac
