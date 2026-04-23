#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
STACK="sportanalytics"

usage() {
  echo "Usage: $0 {build|start|stop|restart|status|logs [service]|test [backend|frontend]}"
  echo ""
  echo "  build              Build backend + frontend Docker images"
  echo "  start              Init swarm + deploy stack"
  echo "  stop               Remove the stack"
  echo "  restart            stop → build → start"
  echo "  status             Show running services"
  echo "  logs [service]     Tail logs (postgres | keycloak | backend | frontend)"
  echo "  test [scope]       Run unit tests (backend | frontend | all)"
  exit 1
}

run_backend_tests() {
  echo "[test] Running backend tests (pytest)..."
  docker run --rm \
    -v "$ROOT/backend:/app" \
    -w /app \
    -e DATABASE_URL="sqlite:///:memory:" \
    -e KEYCLOAK_URL="http://keycloak:8080" \
    python:3.11-slim \
    bash -c "pip install --no-cache-dir -q -r requirements.txt && pytest -v tests/"
}

run_frontend_tests() {
  echo "[test] Running frontend tests (vitest)..."
  docker run --rm \
    -v "$ROOT/frontend:/app" \
    -w /app \
    node:20-alpine \
    sh -c "npm install --silent && npm test"
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

  echo "[stop] Waiting for overlay network to be removed..."
  until ! docker network ls --format '{{.Name}}' 2>/dev/null | grep -q "^${STACK}_default$"; do
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
  test)
    SCOPE="${2:-all}"
    case "$SCOPE" in
      backend)  run_backend_tests ;;
      frontend) run_frontend_tests ;;
      all)      run_backend_tests && run_frontend_tests ;;
      *)        echo "Unknown test scope: $SCOPE"; usage ;;
    esac
    ;;
  *)
    usage
    ;;
esac
