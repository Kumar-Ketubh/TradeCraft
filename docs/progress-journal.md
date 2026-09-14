# TradeCraft — Progress Journal

## Week 2 — Phase 2: Core Management

**Date:** September 2026

### Objectives

- Finalize backend as FastAPI + Python
- User authentication: JWT + bcrypt
- Entity hierarchy: `User` → `Workspace` → `Competitor` → `Source`
- Database migrations (Alembic)
- REST CRUD APIs with ownership enforcement
- Pytest coverage for auth and CRUD isolation
- Frontend integration with live APIs

### Work Completed

**Backend Architecture & Authentication**
- FastAPI + Python, modular layout (`backend/app/core`, `db`, `models`, `schemas`, `routers`, `dependencies`)
- `/auth/register`, `/auth/login`, `/auth/me` endpoints
- bcrypt password hashing, JWT token signing and verification

**Database & Models**
- SQLAlchemy ORM: `User`, `Workspace`, `Competitor`, `Source` with cascading deletes
- Alembic migrations (initial: `5110aac07da3`)
- SQLite fallback for offline dev/testing

**REST Endpoints**
- Workspaces: `POST`, `GET`, `GET/:id`, `PUT/:id`, `DELETE/:id`
- Competitors: `POST /workspaces/:ws_id/competitors`, full CRUD
- Sources: `POST /competitors/:c_id/sources`, full CRUD
- Strict multi-tenant authorization enforced per endpoint

**Testing**
- 12 pytest tests covering registration, login, CRUD, cross-user isolation
- In-memory SQLite + FastAPI TestClient
- 100% pass rate

**Frontend**
- `api.js` JWT client wrapper
- `AuthModal.jsx`, `WorkspaceSelector.jsx`, `SourceManager.jsx`
- Updated `Competitors.jsx` and `Dashboard.jsx` to consume live APIs

### Technical Decisions

| Decision | Choice |
|---|---|
| Backend | FastAPI + Python |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Auth | JWT + bcrypt |
| Token Storage | LocalStorage |

### Known Issues & Fixes

1. **psycopg2 + Python 3.13 ARM build failure**
   - Switched to `psycopg2-binary` pre-compiled wheels

2. **passlib + bcrypt 5.0 incompatibility**
   - Replaced passlib with direct `bcrypt` module calls

### Current Status

| Component | Status |
|---|---|
| Backend framework | ✅ Done |
| Auth (JWT + bcrypt) | ✅ Done |
| Workspace CRUD | ✅ Done |
| Competitor CRUD | ✅ Done |
| Source config | ✅ Done |
| DB ORM & migrations | ✅ Done |
| Backend tests | ✅ Done (12/12 passing) |
| Frontend API integration | ✅ Done |
| Web scraping | ⬜ Phase 3 |
| Change detection | ⬜ Phase 4 |
| AI / LangGraph | ⬜ Phase 5 |

### Next Week (Phase 3)

- Source collector adapters (HTTP, HTML parsing, RSS)
- Snapshot storage system
- Scan execution trigger mechanism

---

## Week 1 — Phase 1: Project Foundation

**Date:** September 2026

### Objectives

- Frontend scaffold (React + Vite)
- Backend scaffold (health check server)
- PostgreSQL setup
- Architecture documentation
- Health checks

### Work Completed

**Frontend**
- Vite + React project with 4 pages: Dashboard, Competitors, Findings, Proposal
- Sidebar navigation (state-based, no React Router)
- Mock data in `src/data/mockData.js`
- Dashboard: stat cards, empty findings, live system status
- Competitors: 6 mock brands with monitored URLs
- System Status polls `/health` on load

**Backend**
- FastAPI scaffold with `GET /health` endpoint
- Returns `{ backend, database, ai_workflow, phase }`
- Database reachability check via psycopg2
- CORS enabled for local dev
- `.env.example` template

**Database**
- PostgreSQL with env var configuration
- `database/schema.sql` with planned tables
- UUID extension enabled

**Documentation**
- `docs/architecture.md` updated
- `docs/progress-journal.md` created
- `.env.example` and `.gitignore` added

### Technical Decisions

| Decision | Choice |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI |
| Database | PostgreSQL |
| CSS | Vanilla CSS |
| Routing | State-based (no React Router) |
| DB driver | psycopg2-binary |

### Current Status

| Component | Status |
|---|---|
| Frontend scaffold | ✅ Done |
| Backend scaffold | ✅ Done |
| Database setup | ✅ Done |
| Health checks | ✅ Done |
| Docs | ✅ Done |
| Auth | ✅ Done |
| Competitor monitoring | ⬜ Not started |
| Change detection | ⬜ Not started |
| AI workflow | ⬜ Not started |
