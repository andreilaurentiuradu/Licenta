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
  echo "  logs [service]   Tail logs (postgres | keycloak | backend | frontend)"
  exit 1
}

build_images() {
  echo "[build] Building backend image..."
  docker build -t sportanalytics-backend:latest "$ROOT/backend"

  echo "[build] Building frontend image..."
  docker build -t sportanalytics-frontend:latest "$ROOT/frontend"

  echo "[build] Cleaning up dangling images..."
  docker image prune -f

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
  echo "    Postgres  → localhost:5432"
  echo "    Keycloak  → http://localhost:8180"
  echo "    Backend   → http://localhost:5000"
  echo "    Frontend  → http://localhost:3000"
  echo ""
  echo "  Use './run.sh logs <service>' to follow logs."
}

stack_stop() {
  echo "[stop] Removing stack '$STACK'..."
  docker stack rm "$STACK"

  echo "[stop] Waiting for stack to be fully removed..."
  until ! docker stack ls --format '{{.Name}}' 2>/dev/null | grep -q "^${STACK}$"; do
    sleep 2
  done
  echo "[stop] Stack removed."
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
    build_images
    swarm_init
    stack_deploy
    ;;
  status)
    docker service ls
    ;;
  logs)
    SERVICE="${2:-backend}"
    docker service logs "${STACK}_${SERVICE}" -f
    ;;
  *)
    usage
    ;;
esac
