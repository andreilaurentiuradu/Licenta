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
│  Backend Flask  (port 5000)  ·  single process                  │
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
│   /api/players/<id>/recommendations → ai-recommendation-service:5004          │
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
├── scripts/
│   ├── seed.py                     # Demo accounts + ~6 months of mock data (run.sh seed)
│   ├── demo_risk.py                # FL demo: target a player's risk to low/medium/high or reset (run.sh risk)
│   └── requirements.txt
├── notebooks/
│   ├── prediction-of-injury-with-logisticregression.ipynb
│   └── federated-learning-injury-prediction.ipynb
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
│   │   ├── routes.py               # /api/fl/train, /api/fl/status, /api/fl/clubs, /internal/trigger
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
│   ├── ai-recommendation-service/                 # AI recommendations via Groq (port 5004)
│   │   ├── app.py
│   │   ├── auth.py
│   │   ├── models.py               # + Recommendation (status: pending/accepted/refused/completed)
│   │   ├── routes.py               # /recommendations: get, generate, accept, refuse, complete
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
        │   ├── auth.js             # login · register · adminCreateUser · getMe · listUsers
        │   ├── players.js          # Player metrics + recommendation actions (accept/refuse/complete)
        │   └── fl.js               # getFlStatus · triggerFLRound · getRiskRanking
        ├── components/
        │   ├── HistoryAccordion.jsx  # Collapsible time-bucketed history (Today/This week/Month/...)
        │   └── ThemedBackground.jsx  # Per-tab decorative motif (health/strength/wellness/...)
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
./run.sh seed     # create demo accounts + populate ~6 months of mock metrics
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
./run.sh logs ai-recommendation-service          # tail AI service logs
./run.sh logs feedback-service    # tail feedback-service logs
./run.sh logs frontend            # tail frontend logs
./run.sh test [scope]             # run tests (auth|player|fl|ai|feedback|frontend|all)
./run.sh seed                     # seed mock player data (idempotent)
./run.sh risk low|medium|high|reset [player]  # FL demo: target a player's risk to a random probability in the chosen zone, or reset to seed data
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

## User Guide — Demo Flow

> **Prerequisites:** stack running (`./run.sh start`), demo data seeded (`./run.sh seed`).
> Open **http://localhost:5000** in the browser.

---

### Admin — `admin1 / admin123`

**Goal:** manage the platform and create accounts for new clubs.

1. **Login** → `admin1` / `admin123` → select sport → Home
2. Home shows the **Admin** badge and the **User Management** card
3. Click **User Management** → create a new coach:
   - Role: `coach`, Club: `FC Test`, fill in username/email/password → Submit
4. Create a new player for that coach's club:
   - Role: `player`, Club: `FC Test`
5. Go to **Profile** → verify roles assigned (admin badge visible)
6. Go to **Support** → FAQ section with platform documentation

> Admins see all navigation cards and bypass club-based filtering.

---

### Coach — `coach2 / coach123` (FC Rivals — high risk club)

**Goal:** monitor player risk, trigger FL training, access individual profiles.

1. **Login** → `coach2` / `coach123` → Home
2. Home shows:
   - **Injury Risk Ranking** panel — 3 players sorted by FL risk score
   - Red alert banner: players with high risk flagged immediately
   - **Federated Learning** panel with current model stats (round, clubs)
3. In the **FL panel** → click **"Start round →"**
   - FL fine-tunes the FC Rivals local model on the seeded data
   - FedAvg aggregates across all clubs → global model updated
   - Round counter increments (quality metrics are visible to admins only)
4. Risk Ranking refreshes — probabilities reflect the updated model
5. Click on a **high-risk player** (e.g. player4 or player5) → navigates to their profile
6. Browse tabs:
   - **Biometrics** — position, height, weight, birth year
   - **Training** — training hours and matches chart (last ~6 months)
   - **Physical** — knee strength, hamstring, reaction time multi-line chart
   - **Injuries** — injury cards with severity and rehab details
   - **Wellness** — sleep, stress, mood and nutrition charts
   - **Recommendations** — AI-generated (Groq) with FL risk score at top
7. Click **Players** card → full player list for FC Rivals only (other clubs not visible)
8. Repeat step 3 logged in as `coach1`, `coach3`, `coach4` to add all 4 clubs to the global model

> Each "Start round →" from a different coach club adds a new FedAvg round. After 4 coaches train, `clubs_count = 4` in the FL panel.

---

### Player — `player4 / player123` (FC Rivals — high risk)

**Goal:** view personal metrics and AI recommendations.

1. **Login** → `player4` / `player123` → Home
2. Home shows the **Player** badge and **My Stats** card
3. Click **My Stats** → Player profile opens at Biometrics tab
4. Browse all tabs:
   - **Training** → chart with training load over ~6 months
   - **Physical** → multi-line chart (knee strength, agility, sprint speed)
   - **Injuries** → injury history cards (2–3 injuries for FC Rivals profile)
   - **Wellness** → sleep hours, stress and mood trends
   - **Recommendations** → FL risk score (High · ~90%+) + 3–4 AI recommendations
     - Injury Prevention (high priority)
     - Training Load adjustment
     - Wellness / Recovery advice
     - **Accept** / **Refuse** (→ a new one of the same category) / **Mark complete** (→ moves to the history list below). Recommendations are persisted — the LLM is not re-called on every visit; use **Generate new** for a fresh set.
5. Add a new wellness entry (click **"+ Add entry"** in Wellness tab):
   - Fill in sleep hours, stress level, mood, calories, hydration → Save
   - FL trigger fires automatically in the background (player-service → fl-service)
6. Go back to **Home** → Recommendations update after FL model re-trains

> A player can only see their own data — navigating to another player's URL returns 403 Forbidden.

---

### FL Pipeline — end-to-end demo sequence

The following sequence demonstrates the full Federated Learning flow:

```
1. ./run.sh seed                        → 4 clubs × 3 players with varied risk profiles

2. Login as coach1 (FC Demo)
   → Home → "Start round →"
   → FL round 1: FC Demo local model trained
   → FedAvg with available clubs → fl_global_models round = 1

3. Login as coach2 (FC Rivals)
   → Home → "Start round →"
   → FL round 2: FC Rivals model trained (high-stress, high-injury data)
   → FedAvg → global model now sees 2 distinct risk profiles

4. Login as coach3 + coach4 → repeat
   → After 4 rounds: clubs_count = 4, global model aggregated across all risk profiles

5. Login as player4 (FC Rivals)
   → Recommendations tab → Injury risk: HIGH (~95%)
   → LLM recommendations calibrated to high-risk context

6. Login as player1 (FC Demo)
   → Recommendations tab → Injury risk: LOW (~4%)
   → LLM recommendations reflect low-risk, maintenance focus

7. Add wellness data for player1 (poor sleep + high stress)
   → FL trigger fires automatically
   → Risk score updates on next page load
```

> Raw player data (wellness, training, physical metrics) never leaves the service.
> Only model weights (LogisticRegression coefficients + intercept) are exchanged between clubs and the central FL server.

> **Quick risk demo (no retraining needed):** `./run.sh risk high player1` writes metrics that push the
> player's feature vector to a high-risk profile (coefficient-aware, so it always crosses the threshold);
> `./run.sh risk low player1` does the opposite, and `./run.sh risk reset player1` restores realistic seed
> data. The script prints the risk **before → after** and the UI reflects it on the next page load.

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
| `POST` | `/api/fl/train` | coach / admin | Trigger an FL round. Coach → own club; admin → a specific club via `{"club": "..."}`, or all clubs if omitted |
| `GET` | `/api/fl/status` | coach / admin | Global model: round, clubs, samples. Quality metrics (accuracy / recall / loss) are **admin-only** |
| `GET` | `/api/fl/clubs` | admin | Clubs with player counts and last local-model state (for per-club training) |
| `GET` | `/api/fl/risk` | coach / admin | Injury risk ranking for all players in the coach's club |
| `GET` | `/internal/risk/<id>` | internal only | FL risk score for a single player (used by ai-recommendation-service) |
| `POST` | `/internal/trigger` | internal only | Called by player-service after data mutations |

### AI Recommendations (ai-recommendation-service)

Recommendations are **persisted** in the `recommendations` table and are **not** regenerated on every page visit. The LLM is called only on the first-ever visit (to populate), on an explicit "Generate new" request, or when a recommendation is refused (one replacement). Each recommendation has a status: `pending`, `accepted`, `refused` or `completed`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/players/<id>/recommendations` | coach / own player | Return stored active + completed recommendations (generates an initial set only when none exist) |
| `POST` | `/api/players/<id>/recommendations/generate` | coach / own player | Force a fresh set (archives current active ones, keeps history) |
| `POST` | `/api/players/<id>/recommendations/<rid>/accept` | coach / own player | Mark a recommendation as accepted |
| `POST` | `/api/players/<id>/recommendations/<rid>/refuse` | coach / own player | Refuse it and return a replacement of the **same category** |
| `POST` | `/api/players/<id>/recommendations/<rid>/complete` | coach / own player | Mark as complete → moves to the completed history |

Generation flow:
1. Fetches the player's FL injury risk score from `fl-service /internal/risk/<id>` — this is the authoritative risk source (returned on every call, never an LLM guess)
2. Collects last 30 days of wellness + training + latest physical assessment
3. Sends both to **Groq API** (`llama-3.1-8b-instant`) via OpenAI-compatible client
4. Stores 3–4 prioritised recommendations (Injury Prevention, Training Load, Wellness, Nutrition, Recovery)

Falls back to a static recommendation pool if `GROQ_API_KEY` is not set (initial set and refuse replacements both use it). The FL risk score is always returned regardless.

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
| `recommendations` | ai | AI recommendations with status (pending/accepted/refused/completed) |
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
- Sport colour theme: emerald green
- Glassmorphism form cards on dark gradient backgrounds
- Recharts time-series visualisations (line, bar, stacked bar) on all metric pages
- Date range picker in player layout — persisted as URL search params (still applies on top of the grouping below)
- Player history (training / physical / wellness / injuries) grouped into collapsible time buckets: Today / This week / This month / Last 3 months / Older
- Recommendations page: accept / refuse (→ a replacement of the same category) / mark complete, with a completed-history section below
- Role-based home dashboard:
  - **Admin** → User Management card + FL admin panel (per-club training + admin-only quality metrics: cross-validated accuracy / recall / log loss)
  - **Coach** → Players card + FL Panel (train button, round/clubs stats) + Injury Risk Ranking (sorted by FL probability, red alert for high-risk players)
  - **Player** → My Stats card

### Tests

Each microservice has its own pytest suite. The frontend uses vitest. All tests run in CI on every push.

**Backend (pytest)** — SQLite in-memory, Keycloak JWT mocked via `pytest-mock`:

| Service | File | Coverage |
|---|---|---|
| auth-service | `test_auth.py` | register validation, role enforcement, `/me`, admin create-user |
| player-service | `test_players.py` | biometrics CRUD + RBAC, training, physical, wellness (nutrition_score), injuries |
| fl-service | `test_fl.py` | status (no model / with model), admin-only metrics, internal trigger, train RBAC, admin per-club training, club listing |
| ai-recommendation-service | `test_ai.py` | RBAC, persisted recommendations (no re-generation), accept / refuse (same-category replacement) / complete, generate, Groq fallback |
| feedback-service | `test_feedback.py` | submit validation, persistence, admin list |

**Frontend (vitest + Testing Library)** — 69 tests across 12 files:

- `AuthContext.test.jsx` — token storage, login, logout, expired token
- `Login.test.jsx` — form rendering, sport default/preserve, navigation
- `Register.test.jsx` — field validation, password mismatch, role/sport dropdowns
- `UserManagement.test.jsx` — admin create-user form, role dropdown
- `AdminUsers.test.jsx` — user list, role filter, search, delete with confirmation
- `Profile.test.jsx` — role badges, initials, Keycloak role filtering
- `Feedback.test.jsx` — star rating aspects, form submission
- `Home.test.jsx` — role-aware cards: admin → User Management, coach → Players, player → My Stats
- `SportSelect.test.jsx` — sport card click, localStorage, navigation
- `PlayerRecommendations.test.jsx` — render, accept, refuse (replacement), complete (history), regenerate refused, interval polling
- `Support.test.jsx` — header, FAQ entries (recommendation actions & history grouping), expand, back navigation
- `ThemedBackground.test.jsx` — variant selection, unknown-variant fallback, decorative/non-interactive glyphs

```bash
./run.sh test all        # all services + frontend
./run.sh test player     # player-service only
./run.sh test frontend   # frontend only
```

**CI/CD (GitHub Actions)** — `.github/workflows/ci.yml`:
- 6 parallel jobs (one per service + frontend)
- Runs on every push to any branch and on every PR targeting `main`
- `All tests passed` job — used as the branch protection status check on `main`
