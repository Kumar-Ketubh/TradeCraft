# TradeCraft — Progress Journal

## Week 2 — Phase 2: Core Management

**Date:** September 2026

---

### Objectives

Implement the foundational user management, multi-tenant workspace context, competitor management, and source URL configuration prior to introducing automated scraping and AI intelligence workflows in later phases.

Phase 2 scope:
- Finalize backend technology as FastAPI + Python
- Implement user authentication with JWT access tokens and bcrypt password hashing
- Model entity hierarchy: `User` ➔ `Workspace` ➔ `Competitor` ➔ `Source` in PostgreSQL with SQLAlchemy ORM
- Database migrations with Alembic
- REST CRUD APIs for Workspaces, Competitors, and Sources with strict ownership enforcement
- Pytest suite covering authentication and CRUD isolation
- Update React frontend to replace mock data with live FastAPI + PostgreSQL API integration

---

### Work Completed

#### Backend Architecture & Authentication
- Finalized FastAPI + Python as the backend stack
- Created modular package layout (`backend/app/` with core, db, models, schemas, routers, dependencies)
- Implemented `/auth/register`, `/auth/login`, and `/auth/me` endpoints
- Passwords hashed securely using `bcrypt`
- Signed JWT access tokens issued upon successful authentication and verified via FastAPI HTTPBearer dependencies

#### Database & Models
- Built SQLAlchemy ORM models: `User`, `Workspace`, `Competitor`, `Source` with cascading deletes and foreign keys
- Set up Alembic migration framework and generated initial migration script (`5110aac07da3`)
- Added lazy database engine initialization with SQLite fallback for offline development/testing

#### REST Endpoints & Multi-Tenant Authorization
- `Workspaces`: `POST /workspaces`, `GET /workspaces`, `GET /workspaces/{id}`, `PUT /workspaces/{id}`, `DELETE /workspaces/{id}`
- `Competitors`: `POST /workspaces/{ws_id}/competitors`, `GET /workspaces/{ws_id}/competitors`, `GET /workspaces/{ws_id}/competitors/{id}`, `PUT`, `DELETE`
- `Sources`: `POST /competitors/{c_id}/sources`, `GET /competitors/{c_id}/sources`, `GET /competitors/{c_id}/sources/{id}`, `PUT`, `DELETE`
- Enforced strict authorization: users can only view, edit, or delete entities within workspaces they own

#### Testing
- Created pytest suite (`backend/tests/`) using in-memory SQLite and FastAPI TestClient
- Added 12 unit tests covering registration, duplicate email handling, login validation, protected endpoints, workspace CRUD, competitor CRUD, source CRUD, and cross-user isolation checks
- All 12 unit tests passing (100% pass rate)

#### Frontend Integration
- Built `api.js` client wrapper supporting JWT authorization headers
- Created `AuthModal.jsx` component for Login and Registration
- Created `WorkspaceSelector.jsx` for selecting active workspace and creating new workspaces
- Created `SourceManager.jsx` for managing competitor source URLs, categories (`website`, `product_page`, `pricing`, `blog`, `documentation`, `rss`, `news`, `other`), and toggling monitoring
- Updated `Competitors.jsx` to fetch and mutate real backend data
- Updated `Dashboard.jsx` to display live health status and workspace summary stats

---

### Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| Backend Framework | FastAPI + Python | Finalized decision for native Python AI ecosystem compatibility |
| ORM | SQLAlchemy 2.0 | Standard Python ORM with declarative models and relation mapping |
| Database Migrations | Alembic | Standard migration tool for SQLAlchemy |
| Authentication | JWT + bcrypt | Secure, stateless authentication suitable for API backend |
| Token Storage | LocalStorage | Simple, clean client-side token storage for prototype stage |

---

### Problems / Challenges

1. **Python 3.13 psycopg2 C extension build failure:**
   - *Problem:* `psycopg2==2.9.9` wheel failed to compile from source on macOS ARM with Python 3.13 due to removed C API functions.
   - *Solution:* Switched to `psycopg2-binary==2.9.13` pre-compiled wheels in `requirements.txt`.

2. **Passlib + Bcrypt 5.0 compatibility issue:**
   - *Problem:* `passlib` trapped `ValueError: password cannot be longer than 72 bytes` during internal initialization checks on modern bcrypt versions.
   - *Solution:* Switched to direct `bcrypt` module calls in `security.py` (`bcrypt.hashpw` and `bcrypt.checkpw`).

---

### Current Status

| Component | Status |
|---|---|
| Backend framework | ✅ Finalized (FastAPI) |
| User authentication | ✅ Done (JWT + bcrypt) |
| Workspace CRUD | ✅ Done |
| Competitor CRUD | ✅ Done |
| Source configuration | ✅ Done |
| Database ORM & Migrations | ✅ Done (SQLAlchemy + Alembic) |
| Backend unit test suite | ✅ Done (12 tests passing) |
| Frontend API integration | ✅ Done |
| Web scraping / source adapters | 🔲 Phase 3 |
| Change detection | 🔲 Phase 4 |
| AI / LangGraph workflow | 🔲 Phase 5 |

---

### Next Week's Plan (Phase 3)

- Implement source collector adapters (HTTP fetching, HTML text extraction, RSS parsing)
- Build snapshot storage system to retain fetched source content history
- Establish initial scan execution trigger mechanism

---

## Week 1 — Phase 1: Project Foundation

**Date:** September 2026

---

### Objectives

Establish the foundational project structure so future phases can build on a clean, well-documented base.

Phase 1 scope:
- Frontend scaffold (React + Vite)
- Backend scaffold (minimal health check server)
- Database setup (PostgreSQL connection configuration)
- Architecture documentation
- Health checks

---

### Work Completed

#### Frontend
- Created Vite + React + JavaScript project (`frontend/`)
- Implemented four main pages: Dashboard, Competitors, Findings, Proposal
- Simple sidebar navigation (no React Router — state-based for simplicity)
- Mock data centralised in `src/data/mockData.js`
- Dashboard displays stat cards, empty findings state, and live system status
- System Status section polls `/health` on load and reflects real backend/DB status
- Competitors page lists 6 mock brands, each with multiple monitored source URLs
- Findings page shows an intentional empty state
- Proposal page shows the planned workflow diagram with a disabled Generate button
- Simple, clean CSS — no component libraries

#### Backend
- Created minimal FastAPI scaffold (`backend/`)
- `GET /health` endpoint returns `{ backend, database, ai_workflow, phase }`
- Database reachability check via `psycopg2` (reads env vars, attempts connect + close)
- CORS enabled for local development
- `requirements.txt` with pinned dependencies
- `.env.example` template (no credentials committed)
- `backend/README.md` with setup instructions

#### Database
- PostgreSQL chosen as the database
- Connection configuration via environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)
- `database/schema.sql` placeholder — enables `uuid-ossp` extension, documents planned tables
- `database/README.md` with setup instructions

#### Documentation
- `docs/architecture.md` updated with Phase 1 status section
- `docs/progress-journal.md` created (this file)
- Root `.env.example` added
- Root `.gitignore` added

---

### Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| Frontend framework | React + Vite | Specified in project requirements |
| Backend scaffold | FastAPI (temporary) | Simpler to scaffold quickly; final choice TBD |
| Database | PostgreSQL | Specified in project requirements |
| CSS | Vanilla CSS | Avoid component library dependency at prototype stage |
| Client-side routing | State-based (no React Router) | Simpler for a 4-page prototype |
| DB driver | psycopg2-binary | Standard PostgreSQL Python driver |

---

### Problems / Challenges

- None major in Phase 1. The frontend and backend are intentionally minimal.

---

### Solutions

- Kept all files simple enough for a student team to explain in a project review.
- Used `AbortSignal.timeout(4000)` on the health fetch so the frontend does not hang if the backend is offline.
- Backend returns `"not_connected"` for AI Workflow explicitly, making the Phase 1 boundary clear in the UI.

---

### Current Status

| Component | Status |
|---|---|
| Frontend scaffold | ✅ Done |
| Backend scaffold | ✅ Done |
| Database setup | ✅ Done (config only) |
| Health checks | ✅ Done |
| Architecture docs | ✅ Done |
| Authentication | ✅ Done |
| Competitor monitoring | 🔲 Not started |
| Change detection | 🔲 Not started |
| AI / LangGraph workflow | 🔲 Not started |
