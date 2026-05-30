# LawrAnalyzer — Predictive Analytics Platform for Elite Sports

A SaaS platform that helps sports clubs anticipate player injuries, support tactical decisions, and optimise training programmes using Federated Learning — a privacy-by-design AI architecture where raw player data never leaves the club's infrastructure.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Authentication | Keycloak 24 (OIDC, RBAC, RS256 JWT) |
| Backend | Python 3.11 · Flask 3 · SQLAlchemy |
| Database | PostgreSQL 16 |
| Frontend | React 18 · Vite · Tailwind CSS · Recharts |
| ML / FL | scikit-learn · custom FedAvg (LogisticRegression, warm-start) |
| AI Recommendations | Groq API · llama-3.1-8b-instant |
| Orchestration | Docker Swarm |
| API Gateway | Nginx (reverse proxy, path-based routing) |

---

## Architecture

### Monolith (previous)

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Frontend  ·  React + Vite  (port 3000)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP  /api/*
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend Flask  (port 5000)  ·  un singur proces                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  app/api/                                                │   │
│  │   keycloak_auth.py   →   /api/auth/me                   │   │
│  │   players.py         →   /api/players/  (CRUD + FL)     │   │
│  │   fl_api.py          →   /api/fl/       (train/status)  │   │
│  │   feedback.py        →   /api/feedback/                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  fl/  (in-process, same PID)                             │   │
│  │   pipeline.py   bootstrap + FedAvg                       │   │
│  │   features.py   feature extraction from DB               │   │
│  │   model.py      LogisticRegression                       │   │
│  │   server.py     fed_avg()                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  AI Recommendations  (inline in players.py)              │   │
│  │   Groq LLM  ← called directly from request handler      │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────┬────────────────────────┬────────────────────────────┘
           │ SQLAlchemy ORM          │ HTTP REST
           ▼                         ▼
┌──────────────────┐       ┌─────────────────────────┐
│  PostgreSQL      │       │  Keycloak  (port 8180)  │
│  (port 5432)     │       │  JWT · RS256 · JWKS     │
└──────────────────┘       └─────────────────────────┘
```

A single container. An FL crash or slow LLM call blocks the entire API.

---

### Microservices (current)

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Frontend  ·  React + Vite  (port 3000)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP  :5000/api/*
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Gateway  ·  Nginx  (port 5000 → 80)   [Docker Swarm]          │
│                                                                 │
│   /api/auth/                        → auth-service:5001        │
│   /api/players/<id>/recommendations → ai-service:5004          │
│   /api/players/                     → player-service:5002      │
│   /api/fl/                          → fl-service:5003          │
│   /api/feedback/                    → feedback-service:5005    │
│   /                                 → frontend:3000            │
└───┬───────────┬──────────┬────────────┬───────────┬────────────┘
    │           │          │            │           │
    ▼           ▼          ▼            ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│ auth   │ │player  │ │  fl    │ │   ai     │ │feedback  │
│service │ │service │ │service │ │ service  │ │ service  │
│ :5001  │ │ :5002  │ │ :5003  │ │  :5004   │ │  :5005   │
│        │ │        │ │        │ │          │ │          │
│register│ │profile │ │ train  │ │  Groq    │ │ submit   │
│login   │ │wellness│ │ status │ │  LLM     │ │ list     │
│me      │ │training│ │FedAvg  │ │ llama-   │ │          │
│users   │ │physical│ │bootstrap│ │3.1-8b   │ │          │
│        │ │injuries│ │        │ │          │ │          │
└───┬────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └────┬─────┘
    │          │    ▲      │           │             │
    │          │    │ HTTP │           │             │
    │          │    │ POST │           │             │
    │          └────┘      │           │             │
    │       /internal/trigger          │             │
    │                                  │             │
    └──────────┬───────────┴─────────┬─┴─────────────┘
               │  SQLAlchemy ORM     │
               │  (shared schema)    │  HTTP REST
               ▼                     ▼
┌──────────────────┐       ┌─────────────────────────┐
│  PostgreSQL      │       │  Keycloak  (port 8180)  │
│  (port 5432)     │       │  JWT · RS256 · JWKS     │
│                  │       │  verified independently │
│  FLGlobalModel   │       │  in each service        │
│  FLClubModel     │       └─────────────────────────┘
│  PlayerProfile   │
│  WellnessLog     │
│  TrainingLog ... │
└──────────────────┘
```

**Federated Learning data flow:**

```
player-service  ──POST /internal/trigger──►  fl-service
  (after any                                   │
   data mutation)                              │ 1. extract_club_dataset()
                                               │ 2. fine-tune local model
                                               │    (warm-start from global weights)
                                               │ 3. save FLClubModel to DB
                                               │ 4. FedAvg across all clubs
                                               │    θ_global = Σ (nₖ/n_total) · θₖ
                                               │ 5. save new FLGlobalModel
                                               ▼
                                         GET /api/fl/status  ◄── Frontend (FLPanel)
```

**Architecture comparison:**

| | Monolith | Microservices |
|---|---|---|
| Containers | 1 Flask process | 7 containers (Swarm) |
| Scaling | all or nothing | per service |
| Fault isolation | FL crash = API down | services fail independently |
| Auth | centralised in backend | JWKS verified locally per service |
| FL trigger | background thread, same process | HTTP inter-service call |
| AI | inline in request handler | dedicated service, isolated API key |

---

## Project Structure

```
.
├── docker-compose.yml              # Docker Swarm stack definition
├── run.sh                          # Build / deploy / test / seed / FL / notebook
├── datasets/
│   └── football_data.csv           # Kaggle dataset (injury prediction, ~800 players)
├── keycloak/
│   └── realm-export.json           # Realm: roles, client, demo users
├── gateway/
│   ├── Dockerfile
│   └── nginx.conf                  # Path-based reverse proxy to all services
├── backend/
│   ├── seed.py                     # Populate mock player data (used by run.sh seed)
│   ├── requirements.txt
│   └── models/
│       ├── data.csv                # Dataset copy for notebooks
│       ├── prediction-of-injury-with-logisticregression.ipynb
│       └── federated-learning-injury-prediction.ipynb
├── services/
│   ├── auth-service/               # Keycloak integration (port 5001)
│   │   ├── app.py
│   │   ├── auth.py                 # JWKS-based JWT verification
│   │   ├── routes.py               # /api/auth/: login, register, me, create-user
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── player-service/             # Player CRUD + metrics (port 5002)
│   │   ├── app.py
│   │   ├── auth.py
│   │   ├── models.py               # PlayerProfile, TrainingLog, PhysicalAssessment,
│   │   │                           # InjuryRecord, WellnessLog
│   │   ├── routes.py               # /api/players/: all metric endpoints
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── fl-service/                 # Federated Learning engine (port 5003)
│   │   ├── app.py
│   │   ├── auth.py
│   │   ├── models.py               # FLGlobalModel, FLClubModel + player read models
│   │   ├── routes.py               # /api/fl/train, /api/fl/status, /internal/trigger
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   ├── data/
│   │   │   └── data.csv            # Copied from datasets/ at build time
│   │   └── fl/
│   │       ├── model.py            # LogisticRegression definition + 12 FEATURES
│   │       ├── pipeline.py         # bootstrap_global_model + FedAvg aggregation
│   │       ├── features.py         # DB → numpy feature vectors + predict_injury_risk
│   │       ├── server.py           # fed_avg() weighted average implementation
│   │       ├── client.py           # Local training client
│   │       └── simulate.py         # Standalone simulation (run.sh fl)
│   ├── ai-service/                 # AI recommendations via Groq (port 5004)
│   │   ├── app.py
│   │   ├── auth.py
│   │   ├── models.py
│   │   ├── routes.py               # GET /api/players/<id>/recommendations
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── feedback-service/           # Feedback submissions (port 5005)
│       ├── app.py
│       ├── auth.py
│       ├── models.py
│       ├── routes.py               # /api/feedback/
│       ├── requirements.txt
│       └── Dockerfile
└── frontend/
    ├── Dockerfile
    ├── vite.config.js
    └── src/
        ├── api/
        │   ├── axios.js            # Axios instance: auth header + token refresh
        │   ├── auth.js             # login · register · adminCreateUser · getMe
        │   ├── players.js          # Player metrics API wrappers
        │   └── fl.js               # getFlStatus()
        ├── contexts/
        │   └── AuthContext.jsx     # JWT parsing, token storage, getMe fallback
        ├── pages/
        │   ├── Login.jsx
        │   ├── Register.jsx
        │   ├── SportSelect.jsx
        │   ├── Home.jsx            # Role-aware dashboard with FLPanel
        │   ├── Profile.jsx
        │   ├── Feedback.jsx
        │   ├── Support.jsx
        │   ├── UserManagement.jsx
        │   ├── PlayersList.jsx
        │   ├── PlayerLayout.jsx
        │   ├── PlayerBiometrics.jsx
        │   ├── PlayerTraining.jsx
        │   ├── PlayerPhysical.jsx
        │   ├── PlayerInjuries.jsx
        │   ├── PlayerWellness.jsx
        │   └── PlayerRecommendations.jsx
        └── test/
            ├── setup.js
            └── renderWithRouter.jsx
```

---

## Running the Application

> **Prerequisites:** Docker Desktop with Swarm mode enabled, `datasets/football_data.csv` present.

### First run

```bash
./run.sh build    # build all 7 Docker images (gateway + 5 services + frontend)
./run.sh start    # init Swarm + deploy stack
./run.sh seed     # create demo accounts + populate 90 days of mock metrics
```

### After code changes

```bash
./run.sh restart  # stop → rebuild → redeploy
```

> After a full restart on a new machine (fresh `pg_data` volume), run `./run.sh seed` once to re-populate data.

### Other commands

```bash
./run.sh stop                     # remove the stack
./run.sh status                   # list running services and replicas
./run.sh logs gateway             # tail Nginx logs
./run.sh logs auth-service        # tail auth-service logs
./run.sh logs player-service      # tail player-service logs
./run.sh logs fl-service          # tail FL service logs (bootstrap + FedAvg rounds)
./run.sh logs ai-service          # tail AI service logs
./run.sh logs feedback-service    # tail feedback-service logs
./run.sh logs frontend            # tail frontend logs
./run.sh test                     # run frontend unit tests (vitest) in Docker
./run.sh seed                     # seed mock player data (idempotent)
./run.sh fl [clubs] [rounds]      # standalone FL simulation (default: 4 clubs, 10 rounds)
./run.sh notebook                 # start Jupyter server at http://localhost:8888
./run.sh db                       # open psql shell in the running Postgres container
```

### Service URLs

| Service | URL |
|---|---|
| Frontend + API Gateway | http://localhost:5000 |
| Keycloak admin console | http://localhost:8180 |
| PostgreSQL | localhost:5432 (internal only) |

---

## Demo Accounts

`admin1` is created from `keycloak/realm-export.json` at startup. All other accounts are created by `./run.sh seed`.

| Username | Password | Role | Club | Notes |
|---|---|---|---|---|
| `admin1` | `admin123` | admin | — | Full platform access |
| `coach1` | `coach123` | coach | FC Demo | Low injury risk club |
| `coach2` | `coach123` | coach | FC Rivals | High injury risk club |
| `coach3` | `coach123` | coach | FC United | Mixed risk club |
| `coach4` | `coach123` | coach | FC Alpha | Overtraining pattern |
| `player1` | `player123` | player | FC Demo | Midfielder · risk: low |
| `player2` | `player123` | player | FC Demo | Forward · risk: low |
| `player3` | `player123` | player | FC Demo | Defender · risk: medium |
| `player4` | `player123` | player | FC Rivals | Forward · risk: high |
| `player5` | `player123` | player | FC Rivals | Goalkeeper · risk: high |
| `player6` | `player123` | player | FC Rivals | Midfielder · risk: medium |
| `player7` | `player123` | player | FC United | Defender · risk: medium |
| `player8` | `player123` | player | FC United | Forward · risk: low |
| `player9` | `player123` | player | FC United | Goalkeeper · risk: high |
| `player10` | `player123` | player | FC Alpha | Midfielder · risk: high |
| `player11` | `player123` | player | FC Alpha | Forward · risk: high |
| `player12` | `player123` | player | FC Alpha | Defender · risk: medium |

The 4 clubs have distinct risk profiles — designed to make FedAvg aggregation observable:
- **FC Demo** — good sleep, low stress, high warmup adherence → 0–1 injuries per player
- **FC Rivals** — poor sleep, high stress, low warmup → 2–3 injuries per player
- **FC United** — mixed profile
- **FC Alpha** — overtraining pattern (high training load + high injury count)

---

## What is Implemented

### Authentication & RBAC

- Keycloak realm `lawranalyzer` auto-imported at container startup
- Three realm roles: `admin`, `coach`, `player`
- JWT verified via Keycloak JWKS endpoint (RS256) — independently in each microservice; no shared secret
- `club` attribute stored in Keycloak user profile; fetched via admin API as fallback when absent from JWT claims

**Endpoints (auth-service)**

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | public | Exchange username + password for JWT |
| `POST` | `/api/auth/register` | public | Create user with role `coach` or `player` |
| `POST` | `/api/auth/admin/create-user` | admin | Create user with any role |
| `GET` | `/api/auth/me` | any token | Return JWT claims (sub, username, email, roles, club) |

### Player Metrics (player-service)

All endpoints require a valid JWT. Players can only access their own data; coach and admin can access any player.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/players/` | List all players in the coach's club |
| `GET / PUT` | `/api/players/<id>/biometrics` | Position, height, weight, birth year |
| `GET / POST / DELETE` | `/api/players/<id>/training` | Training hours, matches played, warmup adherence |
| `GET / POST / DELETE` | `/api/players/<id>/physical` | Knee strength, hamstring, reaction time, balance, sprint speed, agility |
| `GET / POST / DELETE` | `/api/players/<id>/injuries` | Injury records with severity and rehab details |
| `GET / POST / DELETE` | `/api/players/<id>/wellness` | Calories, macros, hydration, sleep, stress, mood |

All list endpoints accept `?from=YYYY-MM-DD&to=YYYY-MM-DD` date filters.

After every data mutation (wellness / training / physical / injury), player-service automatically POSTs to `fl-service /internal/trigger` to schedule a background FL update for that club.

### Federated Learning (fl-service)

Privacy-by-design: raw player data never leaves the service. Only model weights (coefficients + intercept) are exchanged.

**Model:** LogisticRegression with 12 features, `warm_start=True` for incremental fine-tuning.

**12 features** (selected from Kaggle correlation analysis):

| Feature | Source |
|---|---|
| Position | PlayerProfile.position (label-encoded) |
| Previous_Injury_Count | COUNT(InjuryRecord) |
| Knee_Strength_Score | PhysicalAssessment (latest) |
| Hamstring_Flexibility | PhysicalAssessment (latest) |
| Reaction_Time_ms | PhysicalAssessment (latest) |
| Balance_Test_Score | PhysicalAssessment (latest) |
| Sprint_Speed_10m_s | PhysicalAssessment (latest) |
| Agility_Score | PhysicalAssessment (latest) |
| Sleep_Hours_Per_Night | AVG(WellnessLog.sleep_hours, last 90d) |
| Stress_Level_Score | AVG(WellnessLog.stress_level, last 90d) |
| Nutrition_Quality_Score | derived from WellnessLog macros |
| Warmup_Routine_Adherence | AVG(TrainingLog.warmup_adherence, last 90d) |

**Pipeline:**

1. **Bootstrap (round 0)** — on service startup, trains on `datasets/football_data.csv` (~800 players) and stores initial global weights in `fl_global_models`.
2. **Per-club update** — triggered automatically after any data mutation:
   - extracts (X, y) from DB for all players in the club
   - fine-tunes a local LogisticRegression starting from current global weights
   - saves club weights to `fl_club_models` (upsert)
   - runs FedAvg across all clubs: `θ_global = Σ (nₖ / n_total) · θₖ`
   - saves new row in `fl_global_models` (round + 1)
3. **Thread safety** — `threading.Lock()` serialises concurrent aggregations.

**Endpoints (fl-service)**

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/fl/train` | coach / admin | Manually trigger FL round for the coach's club |
| `GET` | `/api/fl/status` | coach / admin | Current global model: round, accuracy, clubs, samples |
| `POST` | `/internal/trigger` | internal only | Called by player-service after data mutations |

### AI Recommendations (ai-service)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/players/<id>/recommendations` | coach / own player | Generate personalised recommendations |

Collects last 30 days of wellness + training + latest physical assessment and sends to **Groq API** (`llama-3.1-8b-instant`) via OpenAI-compatible client. Returns 3–4 prioritised recommendations across categories: Injury Prevention, Training Load, Wellness, Nutrition, Recovery. Falls back to static defaults if `GROQ_API_KEY` is not set.

To enable: add `GROQ_API_KEY=<your_key>` to `.env` at the project root (automatically picked up by `run.sh`).

### Feedback (feedback-service)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/feedback/` | any token | Submit star-rating feedback (4 aspects) |
| `GET` | `/api/feedback/` | admin | List all feedback submissions |

### Database

PostgreSQL 16 — data persists across restarts via named Docker volume `pg_data`.

| Table | Service | Description |
|---|---|---|
| `player_profiles` | player, fl, ai | Static biometric profile per player |
| `training_logs` | player, fl, ai | Daily training hours, matches, warmup adherence |
| `physical_assessments` | player, fl, ai | Periodic physical measurements (6 parameters) |
| `injury_records` | player, fl, ai | Injury history with severity and rehabilitation |
| `wellness_logs` | player, fl, ai | Daily nutrition macros, hydration, sleep, stress, mood |
| `fl_global_models` | fl | Global model weights per FL round |
| `fl_club_models` | fl | Per-club local model weights (latest) |
| `feedback` | feedback | Star-rating feedback submissions |

User identity is owned by Keycloak — no users table in the application database.

### Frontend

| Route | Access | Description |
|---|---|---|
| `/login` | public | Login form |
| `/register` | public | Registration: role (coach / player) + sport selection |
| `/select-sport` | authenticated | Fallback sport picker (new device) |
| `/home` | authenticated | Role-aware dashboard with FL status panel |
| `/profile` | authenticated | Account details and roles |
| `/feedback` | authenticated | Star-rating feedback form |
| `/support` | authenticated | Support page |
| `/admin/users` | admin | Create users with any role |
| `/players` | coach / admin | List all players in the club |
| `/players/:id/biometrics` | coach / own player | Biometric profile view and edit |
| `/players/:id/training` | coach / own player | Training hours and matches charts |
| `/players/:id/physical` | coach / own player | Physical parameters multi-line chart |
| `/players/:id/injuries` | coach / own player | Injury history cards |
| `/players/:id/wellness` | coach / own player | Nutrition, sleep and stress charts |
| `/players/:id/recommendations` | coach / own player | AI-generated personalised recommendations |

**UI highlights:**
- Per-sport colour theme: emerald green (Football) · orange-red (Marathon)
- Glassmorphism form cards on dark gradient backgrounds
- Recharts time-series visualisations (line, bar, stacked bar) on all metric pages
- Date range picker in player layout — persisted as URL search params
- Role-based home dashboard: admin → User Management · coach → Players + FL Panel · player → My Stats

### Tests

Each microservice has its own pytest suite. The frontend uses vitest. All tests run in CI on every push.

**Backend (pytest)** — SQLite in-memory, Keycloak JWT mocked via `pytest-mock`:

| Service | File | Coverage |
|---|---|---|
| auth-service | `test_auth.py` | register validation, role enforcement, `/me`, admin create-user |
| player-service | `test_players.py` | biometrics CRUD + RBAC, training, physical, wellness (nutrition_score), injuries |
| fl-service | `test_fl.py` | status (no model / with model), internal trigger, train RBAC |
| ai-service | `test_ai.py` | RBAC, response structure, Groq fallback to defaults, mock AI call |
| feedback-service | `test_feedback.py` | submit validation, persistence, admin list |

**Frontend (vitest + Testing Library)** — 42 tests across 8 files:

- `AuthContext.test.jsx` — token storage, login, logout, expired token
- `Login.test.jsx` — form rendering, sport default/preserve, navigation
- `Register.test.jsx` — field validation, password mismatch, role/sport dropdowns
- `UserManagement.test.jsx` — admin create-user form, role dropdown
- `Profile.test.jsx` — role badges, initials, Keycloak role filtering
- `Feedback.test.jsx` — star rating aspects, form submission
- `Home.test.jsx` — role-aware cards: admin → User Management, coach → Players, player → My Stats
- `SportSelect.test.jsx` — sport card click, localStorage, navigation

```bash
./run.sh test all        # toate serviciile + frontend
./run.sh test player     # doar player-service
./run.sh test frontend   # doar frontend
```

**CI/CD (GitHub Actions)** — `.github/workflows/ci.yml`:
- 6 joburi paralele (unul per serviciu + frontend)
- Rulează la orice push și pe orice PR spre `main`
- Job `All tests passed` — target pentru branch protection pe `main`
