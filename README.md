# SportAnalytics — Predictive Analytics Platform for Elite Sports

A SaaS platform that helps sports clubs anticipate player injuries, support tactical decisions, and optimise training programmes using Federated Learning — a privacy-by-design AI architecture where raw player data never leaves the club's infrastructure.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Authentication | Keycloak 24 (OIDC, RBAC) |
| Backend | Python 3.11 · Flask 3 |
| Frontend | React 18 · Vite · Tailwind CSS |
| ML / FL | scikit-learn · Flower (FedAvg) |
| Orchestration | Docker Swarm |

---

## Project Structure

```
.
├── docker-compose.yml          # Docker Swarm stack (3 services)
├── run.sh                      # Build / deploy / manage script
├── keycloak/
│   └── realm-export.json       # Realm config: roles, client, demo users
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py
│   ├── config.py
│   └── app/
│       ├── __init__.py
│       └── api/
│           └── keycloak_auth.py
└── frontend/
    ├── Dockerfile
    ├── src/
    │   ├── App.jsx
    │   ├── api/          # axios.js · auth.js
    │   ├── contexts/     # AuthContext.jsx
    │   └── pages/        # SportSelect · Login · Register · Home
    └── vite.config.js
```

---

## Running the Application

> **Prerequisites:** Docker Desktop running with Swarm mode enabled.

### First run

```bash
./run.sh build    # build backend + frontend Docker images
./run.sh start    # init swarm + deploy all services
```

### Subsequent runs (after code changes)

```bash
./run.sh restart  # rebuild images + redeploy
```

### Other commands

```bash
./run.sh stop              # remove the stack
./run.sh status            # list running services
./run.sh logs keycloak     # tail Keycloak logs
./run.sh logs backend      # tail Flask logs
./run.sh logs frontend     # tail Vite logs
```

### Service URLs

| Service | URL |
|---|---|
| Frontend (React) | http://localhost:3000 |
| Keycloak admin console | http://localhost:8180 |
| Backend API (internal) | http://localhost:5000 |

---

## Sprint 1 — Authentication & RBAC ✅

### What is implemented

**Keycloak (identity provider)**
- Realm `sport-analytics` auto-imported on container startup
- Two realm roles: `admin`, `coach`
- Direct access grants enabled (username + password login)
- Demo accounts pre-seeded

| Username | Password | Role |
|---|---|---|
| `admin_user` | `admin123` | admin |
| `coach_user` | `coach123` | coach |

**Backend (Flask)**
- `POST /api/auth/register` — creates a user in Keycloak via admin API and assigns a role
- `GET  /api/auth/me` — verifies the Keycloak JWT (RS256) and returns user claims
- Token verification uses Keycloak's JWKS endpoint (no shared secret)

**Frontend (React)**
- `/` — sport selection landing page: Football or Marathon, full-screen split design with hover animations
- `/login` — sport-themed login form (dark gradient matching selected sport, glassmorphism inputs)
- `/register` — sport-themed registration with role selection (coach / admin)
- `/home` — protected page, shows welcome message and role badge
- Sport context persisted in `localStorage` — drives colour theme across all pages
- Automatic token refresh via Keycloak refresh token
- Role-aware UI (admin vs coach view)

**UI / Design**
- Full-screen split layout on sport selection with expand-on-hover animation
- Floating dot particles and decorative grid lines on all pages
- Per-sport colour theme: emerald green (Football) · orange-red (Marathon)
- Glassmorphism form cards on dark gradient backgrounds
- Slide-up entrance animation on Login and Register

---

## Sprint 2 — Player Management (planned)

- Club registration with team profile (name, city, sport)
- Player roster management: add / edit / delete players
- Player public data: name, position, age, height, weight, nationality
- Player status tracking: active / injured / recovery
- Role-based access: coaches manage their own team only, admins see all

---

## Sprint 3 — Metrics & Injury Risk Prediction (planned)

- Record player training metrics per session:
  - Training hours, matches played, previous injuries
  - Knee strength, hamstring flexibility, reaction time
  - Balance score, sprint speed, agility, sleep, stress, nutrition
- Run injury risk prediction per player using the global ML model
- Risk output: percentage score + level (low / medium / high)
- Prediction history per player

---

## Sprint 4 — Federated Learning (planned)

Privacy-by-design architecture: model weights are shared, raw data never leaves the club.

- Each club trains a local neural network on their own player data
- Only model weights (W₁, b₁, W₂, b₂) are sent to the central server
- Server aggregates updates using **FedAvg**: `θ_global = Σ (nₖ / n_total) × θₖ`
- Aggregation powered by the **Flower** framework
- Global model improves with each participating club while preserving data privacy
- GDPR compliant by design

---

## Sprint 5 — Analytics Dashboard (planned)

- Team-level injury risk overview
- Historical accuracy of the global FL model across rounds
- Participating clubs and their contribution sizes
- Risk distribution charts per position and age group
