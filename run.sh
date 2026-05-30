#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
STACK="lawranalyzer"

# Load .env so docker stack deploy picks up secrets (e.g. OPENAI_API_KEY)
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
fi

# ── FL pip deps installed inline (no separate requirements) ────────────────
FL_DEPS="numpy pandas scikit-learn"
NB_DEPS="notebook numpy pandas scikit-learn matplotlib"

usage() {
  cat <<'EOF'
LawrAnalyzer — Predictive Analytics Platform
Privacy-by-Design · Federated Learning · Injury Prediction

Usage: ./run.sh <command> [args]

  INFRASTRUCTURE
    build                Build backend + frontend Docker images
    start                Init Docker Swarm and deploy stack
    stop                 Remove the running stack
    restart              stop → build → start (full redeploy)
    status               Show running services and replicas
    logs [service]       Tail service logs  (postgres|keycloak|backend|frontend)

  DATA
    seed                 Create demo accounts (admin / coach / 3 players)
                         and populate 90 days of mock metrics in the DB
    db                   Open a psql shell in the running Postgres container

  TESTING
    test [scope]         Run tests: auth|player|fl|ai|feedback|frontend|all (default: all)

  FEDERATED LEARNING
    fl [clubs] [rounds]  Simulate FedAvg injury-prediction training
                         clubs  — number of sports clubs  (default: 4)
                         rounds — FL communication rounds (default: 10)
                         Requires: datasets/football_data.csv  (Kaggle dataset)

    notebook             Start Jupyter server with the ML/FL notebooks
                         Opens on http://localhost:8888
                         Requires: datasets/football_data.csv  (Kaggle dataset)

Examples:
  ./run.sh build && ./run.sh start
  ./run.sh seed
  ./run.sh fl 6 20
  ./run.sh notebook
  ./run.sh logs backend
  ./run.sh test
  ./run.sh db
EOF
  exit 1
}


# ── Infrastructure ─────────────────────────────────────────────────────────

build_images() {
  # Copy dataset into fl-service build context
  if [ -f "$ROOT/datasets/football_data.csv" ]; then
    echo "[build] Copying football_data.csv → services/fl-service/data/football_data.csv"
    mkdir -p "$ROOT/services/fl-service/data"
    cp "$ROOT/datasets/football_data.csv" "$ROOT/services/fl-service/data/football_data.csv"
  else
    echo "[build] WARNING: datasets/football_data.csv not found — FL bootstrap will be skipped."
  fi

  docker build -t lawranalyzer-gateway:latest  "$ROOT/gateway"
  docker build -t lawranalyzer-auth:latest     "$ROOT/services/auth-service"
  docker build -t lawranalyzer-player:latest   "$ROOT/services/player-service"
  docker build -t lawranalyzer-fl:latest       "$ROOT/services/fl-service"
  docker build -t lawranalyzer-ai:latest       "$ROOT/services/ai-service"
  docker build -t lawranalyzer-feedback:latest "$ROOT/services/feedback-service"
  docker build -t lawranalyzer-frontend:latest "$ROOT/frontend"

  docker image prune -f
  echo "[build] Done."
}

swarm_init() {
  if ! docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q active; then
    echo "[swarm] Initialising Docker Swarm..."
    docker swarm init
  else
    echo "[swarm] Swarm already active."
  fi
}

stack_deploy() {
  echo "[deploy] Deploying stack '$STACK'..."
  cd "$ROOT"
  docker stack deploy -c docker-compose.yml "$STACK"

  cat <<'EOF'

  Services:
    Postgres         → localhost:5432 (internal only)
    Keycloak         → http://localhost:8180   (admin / admin123)
    Gateway (API)    → http://localhost:5000
    Frontend         → http://localhost:5000   (served via gateway)

  Microservices (internal, via gateway on port 5000):
    auth-service     → /api/auth/
    player-service   → /api/players/
    fl-service       → /api/fl/
    ai-service       → /api/players/<id>/recommendations
    feedback-service → /api/feedback/

  Demo accounts (run ./run.sh seed first):
    admin1   / admin123    role: admin
    coach1   / coach123    role: coach
    player1  / player123   role: player
    player2  / player123   role: player
    player3  / player123   role: player

  Tip: ./run.sh logs <service>   to follow a service's output.
EOF
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


# ── Testing ────────────────────────────────────────────────────────────────

run_service_tests() {
  local SVC="$1"
  echo "[test] Running ${SVC} tests (pytest)..."
  WIN_ROOT="$(cd "$ROOT" && pwd -W 2>/dev/null || echo "$ROOT")"
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "${WIN_ROOT}/services/${SVC}:/app" \
    -w /app \
    -e DATABASE_URL="sqlite:///:memory:" \
    -e KEYCLOAK_URL="http://localhost" \
    -e KEYCLOAK_REALM="test" \
    python:3.11-slim \
    bash -c "pip install --no-cache-dir -q -r requirements.txt && pytest tests/ -v --tb=short"
}

run_frontend_tests() {
  echo "[test] Running frontend tests (vitest)..."
  cd "$ROOT/frontend"
  npm install --silent
  npm test -- --run
  cd "$ROOT"
}


# ── Data ───────────────────────────────────────────────────────────────────

run_seed() {
  echo "[seed] Seeding demo accounts and mock player metrics..."
  WIN_ROOT="$(cd "$ROOT" && pwd -W 2>/dev/null || echo "$ROOT")"
  MSYS_NO_PATHCONV=1 docker run --rm \
    --network "${STACK}_default" \
    -v "${WIN_ROOT}/scripts:/app" \
    -w /app \
    -e KEYCLOAK_URL="http://keycloak:8080" \
    -e DATABASE_URL="postgresql://sa_user:sa_pass@postgres:5432/lawranalyzer" \
    python:3.11-slim \
    bash -c "pip install --no-cache-dir -q -r requirements.txt && python seed.py"
}

open_db_shell() {
  echo "[db] Connecting to Postgres (lawranalyzer)..."
  CONTAINER=$(docker ps --filter "name=${STACK}_postgres" --format "{{.ID}}" | head -1)
  if [ -z "$CONTAINER" ]; then
    echo "[db] ERROR: Postgres is not running. Start the stack first: ./run.sh start"
    exit 1
  fi
  docker exec -it "$CONTAINER" psql -U sa_user -d lawranalyzer
}


# ── Federated Learning ─────────────────────────────────────────────────────

run_fl_simulate() {
  N_CLUBS="${1:-4}"
  FL_ROUNDS="${2:-10}"
  DATA_FILE="$ROOT/services/fl-service/data/football_data.csv"

  if [ ! -f "$DATA_FILE" ] && [ -f "$ROOT/datasets/football_data.csv" ]; then
    mkdir -p "$ROOT/services/fl-service/data"
    cp "$ROOT/datasets/football_data.csv" "$DATA_FILE"
  fi

  if [ ! -f "$DATA_FILE" ]; then
    cat <<EOF
[fl] ERROR: Kaggle dataset not found.

  Expected path : datasets/football_data.csv
  Download from : https://www.kaggle.com/datasets/

Place football_data.csv in datasets/ and re-run: ./run.sh fl ${N_CLUBS} ${FL_ROUNDS}
EOF
    exit 1
  fi

  echo "[fl] Federated Learning simulation — ${N_CLUBS} clubs · ${FL_ROUNDS} rounds"
  echo "[fl] Privacy guarantee: raw player data never leaves any club."
  echo "[fl] Only model weights (coef + intercept) are exchanged with the server."
  echo ""

  WIN_ROOT="$(cd "$ROOT" && pwd -W 2>/dev/null || echo "$ROOT")"
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "${WIN_ROOT}/services/fl-service:/app" \
    -w /app \
    python:3.11-slim \
    bash -c "pip install --no-cache-dir -q ${FL_DEPS} && \
             python -m fl.simulate --clubs ${N_CLUBS} --rounds ${FL_ROUNDS}"
}

run_notebook() {
  echo "[notebook] Starting Jupyter notebook server..."
  echo "[notebook] Open http://localhost:8888 in your browser."
  echo "[notebook] Press Ctrl-C to stop."
  echo ""

  WIN_ROOT="$(cd "$ROOT" && pwd -W 2>/dev/null || echo "$ROOT")"
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "${WIN_ROOT}/notebooks:/notebooks" \
    -w /notebooks \
    -p 8888:8888 \
    python:3.11-slim \
    bash -c "pip install --no-cache-dir -q ${NB_DEPS} && \
             jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root \
               --NotebookApp.token='' --NotebookApp.password=''"
}


# ── Command dispatch ───────────────────────────────────────────────────────

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
  seed)
    run_seed
    ;;
  db)
    open_db_shell
    ;;
  test)
    SCOPE="${2:-all}"
    case "$SCOPE" in
      auth)     run_service_tests auth-service ;;
      player)   run_service_tests player-service ;;
      fl)       run_service_tests fl-service ;;
      ai)       run_service_tests ai-service ;;
      feedback) run_service_tests feedback-service ;;
      frontend) run_frontend_tests ;;
      all)
        run_service_tests auth-service
        run_service_tests player-service
        run_service_tests fl-service
        run_service_tests ai-service
        run_service_tests feedback-service
        run_frontend_tests
        ;;
      *) echo "Unknown scope '$SCOPE'  (auth|player|fl|ai|feedback|frontend|all)"; exit 1 ;;
    esac
    ;;
  fl)
    run_fl_simulate "${2:-4}" "${3:-10}"
    ;;
  notebook)
    run_notebook
    ;;
  *)
    usage
    ;;
esac
