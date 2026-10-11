# TradeCraft — Progress Journal

## Week 4 — Phase 4: Deterministic Change Detection & Classification

**Date:** October 2026

---

### Objectives
Implement deterministic change detection, diff computation, change hashing, heuristic meaningfulness classification, and frontend diff inspection.

### Work Completed

#### Data Layer & Migrations
- Created relational `Change` model in `backend/app/models/change.py` with foreign keys to `workspaces`, `competitors`, `sources`, `scan_runs`, `previous_snapshot_id`, and `current_snapshot_id`.
- Added fields for deterministic change hash (SHA-256), change category (`pricing_change`, `feature_announcement`, `documentation_update`, `blog_post`, `positioning_shift`, `noise`, `unknown`), boolean `is_meaningful`, confidence/significance score (0.0 to 1.0), summary, line-by-line unified diff, and structured diff statistics JSON.
- Created and executed Alembic migration `8c9d0e1f2a3b_create_changes_table.py` supporting PostgreSQL and SQLite fallback with cascading foreign key deletions.

#### Deterministic Diff Engine
- Built `DiffEngine` in `backend/app/diff/engine.py` using Python's standard `difflib.unified_diff`.
- Computes structured statistics: lines added/removed, characters added/removed, and content similarity ratio.
- Generates a deterministic 64-character SHA-256 hash from normalized diff text to ensure identical content changes produce identical change records.

#### Meaningfulness & Category Classifier
- Built `MeaningfulnessClassifier` in `backend/app/classifiers/meaningfulness.py`.
- Suppresses cosmetic noise: whitespace fluctuations, punctuation, copyright year roll-forwards, session IDs, and cookie/privacy banner updates (`is_meaningful=False`, category `"noise"`).
- Categorizes substantive changes:
  - `pricing_change`: Price alterations, dollar/currency changes, tier additions, discounts.
  - `feature_announcement`: New product capabilities, launches, changelog entries, version increments.
  - `blog_post` / `documentation_update`: Knowledge base and article publications.
- Pure heuristic-first execution requiring zero external paid LLM dependencies.

#### Change Detection Service & REST APIs
- Built `ChangeDetectionService` in `backend/app/services/change_service.py` comparing newly ingested snapshots against prior successful snapshots.
- Integrated into `ScanService` so scans automatically trigger change detection upon snapshot persistence.
- Implemented REST endpoints in `backend/app/routers/changes.py`:
  - `GET /workspaces/{id}/changes`: Paginated, filterable by `is_meaningful`, `category`, and `competitor_id`.
  - `GET /changes/{id}`: Detailed change view with full unified diff.
  - `GET /scans/{id}/changes`: Changes detected during a specific scan run.

#### Frontend Intelligence Feed & UI Polish
- Built `DiffViewer.jsx`: Syntax-highlighted unified diff viewer (green additions, red deletions, neutral line headers).
- Built `ChangeCard.jsx`: Minimalist card showing competitor badge, category pill, significance score, and diff summary.
- Updated `Findings.jsx`: Live detected changes feed with quick filters (All vs Meaningful Only, Category filter).
- Redesigned `Dashboard.jsx`: Minimalist layout with live metric cards, recent scans table, and recent intelligence items.
- Polished `Topbar.jsx`: Responsive layout with clean 3px-spaced action buttons (Notification Bell, Theme Toggle, User Profile) and viewport-bounded popovers.

#### Testing & Verification
- Authored extensive pytest suite covering diff engine, meaningfulness classifier, adversarial edge cases, and end-to-end change workflows.
- Full test suite: **206/206 tests passing**.

---

## Week 3 — Phase 3: Data Collection & Snapshot Storage Engine

**Date:** October 2026

---

### Objectives
Implement non-blocking source adapters (`HtmlAdapter`, `RssAdapter`), snapshot storage, content normalization, and scan orchestration.

### Work Completed

#### Data Layer & Migrations
- Created `ScanRun` and `Snapshot` relational models with cascading foreign keys and indexes.
- Created and executed Alembic migration `7a8b9c0d1e2f_create_scan_runs_and_snapshots_tables.py`.

#### Ingestion Adapters & Content Normalization
- Implemented `BaseAdapter`, `HtmlAdapter`, and `RssAdapter` in `backend/app/adapters/`.
- Built deterministic content normalization stripping dynamic boilerplate (`<script>`, `<style>`, `<nav>`, `<footer>`, ad containers).
- Built SHA-256 deterministic content hasher producing identical hashes for semantically identical page text.
- Added adapter factory selecting appropriate parser based on source type.

#### Scan Orchestration Engine
- Implemented `ScanService` in `backend/app/services/scan_service.py`.
- Supports workspace-wide concurrent scans (`POST /workspaces/{id}/scan`) and single-competitor scans (`POST /competitors/{id}/scan`).
- Resilient per-source execution: bounded streaming fetch preventing indefinite hangs; 403, 404, 500, or network timeouts record error snapshots without failing the entire batch scan.
- Exposed scan and snapshot retrieval REST endpoints in `backend/app/routers/scans.py`.

#### Frontend Integration
- Added on-demand "Run Workspace Scan" and competitor scan buttons with live loading spinners.
- Added `SnapshotHistoryModal.jsx` to view historical snapshots and raw content.
- Added scan history execution logs to the dashboard.

---

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
