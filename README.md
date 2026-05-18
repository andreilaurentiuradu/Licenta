# SportAnalytics — Predictive Analytics Platform for Elite Sports

A SaaS platform that helps sports clubs anticipate player injuries, support tactical decisions, and optimise training programmes using Federated Learning — a privacy-by-design AI architecture where raw player data never leaves the club's infrastructure.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Authentication | Keycloak 24 (OIDC, RBAC) |
| Backend | Python 3.11 · Flask 3 · SQLAlchemy |
| Database | PostgreSQL 16 |
| Frontend | React 18 · Vite · Tailwind CSS · Recharts |
| ML / FL | scikit-learn · Flower (FedAvg) *(planned)* |
| Orchestration | Docker Swarm |

---

## Project Structure

```
.
├── docker-compose.yml          # Docker Swarm stack (4 services)
├── run.sh                      # Build / deploy / test / seed script
├── keycloak/
│   └── realm-export.json       # Realm config: roles, client, all demo users
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py
│   ├── config.py
│   ├── seed.py                 # Populate mock player data (idempotent)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── extensions.py       # SQLAlchemy instance
│   │   ├── models.py           # Feedback, PlayerProfile, TrainingLog,
│   │   │                       # PhysicalAssessment, InjuryRecord, WellnessLog
│   │   └── api/
│   │       ├── keycloak_auth.py  # Auth endpoints + token decorator
│   │       ├── feedback.py       # Feedback endpoints
│   │       └── players.py        # Player metrics endpoints
│   └── tests/
│       ├── conftest.py
│       ├── test_auth_me.py
│       ├── test_feedback.py
│       ├── test_keycloak_helpers.py
│       └── test_register.py
└── frontend/
    ├── Dockerfile
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── api/
        │   ├── axios.js          # Axios instance with auth header + refresh
        │   ├── auth.js           # login · register · adminCreateUser · getMe
        │   └── players.js        # Player metrics API wrappers
        ├── contexts/
        │   └── AuthContext.jsx   # JWT parsing (sub, roles), token storage
        ├── pages/
        │   ├── Login.jsx         # Neutral login form (defaults sport to football)
        │   ├── Register.jsx      # Public registration with role + sport dropdown
        │   ├── SportSelect.jsx   # Fallback sport picker (post-login, new device)
        │   ├── Home.jsx          # Role-aware dashboard
        │   ├── Profile.jsx       # Account info + assigned roles
        │   ├── Feedback.jsx      # Star-rating feedback form
        │   ├── Support.jsx       # Support page
        │   ├── UserManagement.jsx # Admin-only: create users of any role
        │   ├── PlayersList.jsx   # Coach: list all players; player: self-redirect
        │   ├── PlayerLayout.jsx  # Shared tab nav + date range picker
        │   ├── PlayerBiometrics.jsx
        │   ├── PlayerTraining.jsx
        │   ├── PlayerPhysical.jsx
        │   ├── PlayerInjuries.jsx
        │   └── PlayerWellness.jsx
        └── test/
            ├── setup.js
            └── renderWithRouter.jsx
```

---

## Running the Application

> **Prerequisites:** Docker Desktop with Swarm mode enabled.

### First run

```bash
./run.sh build    # build backend + frontend Docker images
./run.sh start    # init swarm + deploy all services
./run.sh seed     # create demo player accounts + populate mock data
```

### Subsequent runs (after code changes)

```bash
./run.sh restart  # stop → rebuild → redeploy
```

> After a full restart on a new machine (fresh `pg_data` volume), run `./run.sh seed` once to re-populate player metrics.

### Other commands

```bash
./run.sh stop                  # remove the stack
./run.sh status                # list running services
./run.sh logs postgres         # tail PostgreSQL logs
./run.sh logs keycloak         # tail Keycloak logs
./run.sh logs backend          # tail Flask logs
./run.sh logs frontend         # tail Vite logs
./run.sh test backend          # run pytest in Docker
./run.sh test frontend         # run vitest in Docker
./run.sh test all              # run all tests
./run.sh seed                  # seed mock player data (idempotent)
```

### Service URLs

| Service | URL |
|---|---|
| Frontend (React) | http://localhost:3000 |
| Keycloak admin console | http://localhost:8180 |
| Backend API | http://localhost:5000 |
| PostgreSQL | localhost:5432 |

---

## Demo Accounts

All accounts are created automatically on Keycloak startup from `realm-export.json`.

| Username | Password | Role | Notes |
|---|---|---|---|
| `admin_user` | `admin123` | admin | Full platform access |
| `coach_user` | `coach123` | coach | Sees all players and their metrics |
| `player1` | `player123` | player | Midfielder · mock data pre-seeded |
| `player2` | `player123` | player | Forward · mock data pre-seeded |
| `player3` | `player123` | player | Defender · mock data pre-seeded |

---

## What is implemented

### Authentication & RBAC

**Keycloak (identity provider)**
- Realm `sport-analytics` auto-imported on container startup
- Three realm roles: `admin`, `coach`, `player`
- Direct access grants enabled (username + password login)
- JWT verified via Keycloak JWKS endpoint (RS256, no shared secret)
- Sport selection stored in `localStorage` — set during registration, defaulted to `football` on first login

**Backend auth endpoints**

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | public | Create user with role `coach` or `player` |
| `POST` | `/api/auth/admin/create-user` | admin | Create user with any role |
| `GET` | `/api/auth/me` | any token | Return JWT claims (sub, username, email, roles) |

**User management rules**
- Public registration (`/register`) only accepts `coach` and `player` roles; sport is chosen at registration
- Admin role can only be assigned by an existing admin via User Management

### Player Metrics

**Backend endpoints** — all require a valid token; player can only access their own data, coach/admin can access any player

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/players/` | List all players (coach/admin only) |
| `GET/PUT` | `/api/players/<id>/biometrics` | Profile: position, height, weight, birth year |
| `GET/POST/DELETE` | `/api/players/<id>/training` | Training hours + matches played per day |
| `GET/POST/DELETE` | `/api/players/<id>/physical` | Knee strength, hamstring flexibility, reaction time |
| `GET/POST/DELETE` | `/api/players/<id>/injuries` | Injury records with severity and rehab details |
| `GET/POST/DELETE` | `/api/players/<id>/wellness` | Nutrition macros, hydration, sleep, stress, mood |

All list endpoints accept `?from=YYYY-MM-DD&to=YYYY-MM-DD` date range filters.

### Database

PostgreSQL 16 — data persists across restarts via named Docker volume `pg_data`.

| Table | Description |
|---|---|
| `feedback` | Star-rating feedback submissions |
| `player_profiles` | Static biometric profile per player |
| `training_logs` | Daily training hours and match counts |
| `physical_assessments` | Periodic physical parameter measurements |
| `injury_records` | Injury history with severity and rehabilitation |
| `wellness_logs` | Daily nutrition, sleep, stress and mood logs |

User identity is owned by Keycloak — no users table in the application database.

### Frontend Pages

| Route | Access | Description |
|---|---|---|
| `/login` | public | Neutral login form; defaults sport to football |
| `/register` | public | Registration: role (coach/player) + sport selection |
| `/select-sport` | authenticated | Fallback sport picker for users on a new device |
| `/home` | authenticated | Role-aware dashboard (different cards per role) |
| `/profile` | authenticated | Account details and assigned roles |
| `/feedback` | authenticated | Star-rating feedback form (4 aspects) |
| `/support` | authenticated | Support page |
| `/admin/users` | admin | Create users with any role |
| `/players` | coach / admin | List all players with profile summaries |
| `/players/:id/biometrics` | coach / own player | Biometric profile view and edit |
| `/players/:id/training` | coach / own player | Training hours + matches charts and log |
| `/players/:id/physical` | coach / own player | Physical parameters multi-line chart |
| `/players/:id/injuries` | coach / own player | Injury history cards |
| `/players/:id/wellness` | coach / own player | Nutrition, sleep and stress charts |

**UI highlights**
- Per-sport colour theme: emerald green (Football) · orange-red (Marathon)
- Glassmorphism form cards on dark gradient backgrounds with floating dot particles
- Recharts time-series visualisations (line, bar, stacked bar) on all metric pages
- Date range picker in player layout — persisted as URL search params (shareable links)
- Role-based home dashboard: admin → User Management · coach → Players · player → My Stats

### Tests

**Backend (pytest)** — 36 tests across 4 files:
- `test_auth_me.py` — `/me` endpoint: auth required, role claims, sub field
- `test_feedback.py` — submit / list feedback, model serialisation
- `test_keycloak_helpers.py` — `_create_user_in_keycloak` helper, role constants
- `test_register.py` — public register (coach/player only), admin create-user

**Frontend (vitest + Testing Library)** — 42 tests across 8 files:
- `AuthContext.test.jsx` — token storage, login (username + sub parsing), logout, expired token
- `Login.test.jsx` — form rendering, always navigates to `/home`, sport default/preserve
- `Register.test.jsx` — field validation, password mismatch, role/sport dropdowns, localStorage
- `UserManagement.test.jsx` — admin create-user form, role dropdown
- `Profile.test.jsx` — role badges, initials, Keycloak role filtering
- `Feedback.test.jsx` — star rating aspects, form submission
- `Home.test.jsx` — role-aware cards: admin→User Management, coach→Players, player→My Stats
- `SportSelect.test.jsx` — sport card click, localStorage, navigates to `/home`

---

## Sprint 3 — Federated Learning, AI Recommendations & Live Data *(planned)*

- **Federated Learning** — global model trained across clubs using FedAvg; each club contributes local model weights without sharing raw player data; global baseline dataset used for model initialisation
- **AI Recommendations** — per-player personalised recommendations generated via OpenAI API based on current metrics, injury history and wellness trends
- **Coach Alerts** — automatic alerts triggered when player metrics cross configurable risk thresholds (e.g. sleep quality drop, high stress, injury recurrence risk)
- **Live wearable data ingestion** — real-time data collection from Samsung Gear S3 (heart rate, steps, sleep stages, stress index) via Tizen Web API or companion app
- **Predictive models** — dedicated ML models for sleep quality prediction, stress level classification and injury risk scoring based on accumulated player data

---

## Sprint 4 — Federated Learning *(planned)*

Privacy-by-design: model weights are shared, raw data never leaves the club.

- Each club trains a local neural network on its own player data
- Only model weights are sent to the central server
- Server aggregates using **FedAvg**: `θ_global = Σ (nₖ / n_total) × θₖ`
- Powered by the **Flower** framework
- GDPR compliant by design

---

## Sprint 5 — Analytics Dashboard *(planned)*

- Team-level injury risk overview
- FL model accuracy history across aggregation rounds
- Participating clubs and contribution sizes
- Risk distribution charts by position and age group
