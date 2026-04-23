# SportAnalytics — Predictive Analytics Platform for Elite Sports

A SaaS platform that helps sports clubs anticipate player injuries, support tactical decisions, and optimise training programmes using Federated Learning — a privacy-by-design AI architecture where raw player data never leaves the club's infrastructure.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Authentication | Keycloak 24 (OIDC, RBAC) |
| Backend | Python 3.11 · Flask 3 · SQLAlchemy |
| Database | PostgreSQL 16 |
| Frontend | React 18 · Vite · Tailwind CSS |
| ML / FL | scikit-learn · Flower (FedAvg) *(planned)* |
| Orchestration | Docker Swarm |

---

## Project Structure

```
.
├── docker-compose.yml          # Docker Swarm stack (4 services)
├── run.sh                      # Build / deploy / test / manage script
├── keycloak/
│   └── realm-export.json       # Realm config: roles, client, demo users
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py
│   ├── config.py
│   ├── pytest.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── extensions.py       # SQLAlchemy instance
│   │   ├── models.py           # Feedback model
│   │   └── api/
│   │       ├── keycloak_auth.py  # Auth endpoints + token decorator
│   │       └── feedback.py       # Feedback endpoints
│   └── tests/
│       ├── conftest.py           # Fixtures: app, client, db, mock tokens
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
        │   ├── axios.js          # Axios instance with auth header
        │   └── auth.js           # login · register · adminCreateUser · getMe
        ├── contexts/
        │   └── AuthContext.jsx   # JWT parsing, token storage, login/logout
        ├── pages/
        │   ├── SportSelect.jsx   # Landing: choose Football or Marathon
        │   ├── Login.jsx         # Sport-themed login form
        │   ├── Register.jsx      # Public registration (coach / player)
        │   ├── Home.jsx          # Protected home with role-aware nav cards
        │   ├── Profile.jsx       # Account info + assigned roles
        │   ├── Feedback.jsx      # Star-rating feedback form
        │   ├── Support.jsx       # Support page
        │   └── UserManagement.jsx # Admin-only: create users of any role
        └── test/
            ├── setup.js          # jest-dom, cleanup, toast mock
            └── renderWithRouter.jsx
```

---

## Running the Application

> **Prerequisites:** Docker Desktop with Swarm mode enabled.

### First run

```bash
./run.sh build    # build backend + frontend Docker images
./run.sh start    # init swarm + deploy all services
```

### Subsequent runs (after code changes)

```bash
./run.sh restart  # stop → rebuild → redeploy
```

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
./run.sh test                  # run all tests
```

### Service URLs

| Service | URL |
|---|---|
| Frontend (React) | http://localhost:3000 |
| Keycloak admin console | http://localhost:8180 |
| Backend API | http://localhost:5000 |
| PostgreSQL | localhost:5432 |

---

## What is implemented

### Authentication & RBAC

**Keycloak (identity provider)**
- Realm `sport-analytics` auto-imported on container startup
- Three realm roles: `admin`, `coach`, `player`
- Direct access grants enabled (username + password login)
- JWT verified via Keycloak JWKS endpoint (RS256, no shared secret)
- Demo accounts pre-seeded:

| Username | Password | Role |
|---|---|---|
| `admin_user` | `admin123` | admin |
| `coach_user` | `coach123` | coach |

**Backend endpoints**

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | public | Create user with role `coach` or `player` |
| `POST` | `/api/auth/admin/create-user` | admin | Create user with any role |
| `GET` | `/api/auth/me` | any token | Return JWT claims (username, email, roles) |
| `POST` | `/api/feedback/` | any token | Submit star-rating feedback |
| `GET` | `/api/feedback/` | admin | List all submitted feedback |

**User management rules**
- Public registration (`/register`) only accepts `coach` and `player` roles
- Admin role can only be assigned by an existing admin via `/admin/create-user`

### Database

- PostgreSQL 16 stores application data; data persists across restarts via a named Docker volume (`pg_data`)
- User identity is owned by Keycloak — no users table in the application database
- **Feedback** table: `id`, `user_id` (Keycloak sub), `username`, `ratings` (JSON), `message`, `created_at`

### Frontend pages

| Route | Access | Description |
|---|---|---|
| `/` | public | Sport selection (Football / Marathon) |
| `/login` | public | Sport-themed login |
| `/register` | public | Registration with coach or player role |
| `/home` | authenticated | Role-aware dashboard with navigation cards |
| `/profile` | authenticated | Account details and assigned roles |
| `/feedback` | authenticated | Star-rating feedback form (4 aspects) |
| `/support` | authenticated | Support page |
| `/admin/users` | admin only | Create users with any role |

**UI highlights**
- Full-screen sport-split landing with expand-on-hover animation
- Per-sport colour theme: emerald green (Football) · orange-red (Marathon)
- Glassmorphism form cards on dark gradient backgrounds with floating dot particles
- Slide-up entrance animations throughout
- Keycloak error descriptions surfaced as toast notifications on login failure

### Tests

**Backend (pytest)** — 36 tests across 4 files:
- `test_auth_me.py` — `/me` endpoint: auth required, role claims
- `test_feedback.py` — submit / list feedback, model serialisation
- `test_keycloak_helpers.py` — `_create_user_in_keycloak` helper, role constants
- `test_register.py` — public register (coach/player only), admin create-user

**Frontend (vitest + Testing Library)** — 39 tests across 8 files:
- `AuthContext.test.jsx` — token storage, login, logout, expired token handling
- `Login.test.jsx` — form rendering, submit flow, error toasts
- `Register.test.jsx` — field validation, password mismatch, role restriction
- `UserManagement.test.jsx` — admin create-user form, role dropdown
- `Profile.test.jsx` — role badges, initials, Keycloak role filtering
- `Feedback.test.jsx` — star rating aspects, form submission
- `Home.test.jsx` — role-aware nav cards
- `SportSelect.test.jsx` — sport card click, localStorage, navigation

---

## Sprint 2 — Player Management *(planned)*

- Club registration with team profile (name, city, sport)
- Player roster: add / edit / delete players
- Player public data: name, position, age, height, weight, nationality
- Player status: active / injured / recovery
- Role-based access: coaches manage their own team; admins see all

---

## Sprint 3 — Metrics & Injury Risk Prediction *(planned)*

- Record training metrics per session (hours, injuries, strength, flexibility, sprint speed, sleep, stress, nutrition)
- Injury risk score per player: percentage + level (low / medium / high)
- Prediction history per player

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
