# TradeCraft

## AI Competitive Intelligence & Proposal Generator

An agentic competitive-intelligence platform that monitors competitor changes, investigates their significance, verifies supporting evidence, and generates actionable insights and project proposals.

## Overview

Teams often monitor competitors manually across pricing pages, product pages, changelogs, blogs, public repositories, and announcements.

Existing change-monitoring tools can identify that a page changed, but they do not explain:

- What changed?
- Why does it matter?
- What evidence supports the conclusion?
- What should we consider doing next?

TradeCraft addresses that gap by combining source monitoring, change detection, agentic research, impact analysis, verification, and proposal generation into a single continuous pipeline.

### Core Workflow

```text
What Changed? (Ingestion & Unified Diff)
      ↓
Why Does It Matter? (Context Researcher & Impact Analyzer)
      ↓
What Evidence Supports It? (Critic / Verifier with EGA Threshold)
      ↓
What Should We Consider Doing Next? (Actionable Countermeasures)
      ↓
Generate a Project Proposal (7-Section Executive Document)
```

## Key Features

- **Multi-Tenant Workspace & Competitor Management**: Isolate competitor sources, snapshots, diffs, and findings by workspace.
- **Automated Ingestion Adapters**: Robust fetching with boilerplate suppression for HTML web pages and RSS/Atom syndication feeds.
- **Deterministic Snapshot & Diff Engine**: Myers diff algorithm with SHA-256 content and change hashing.
- **Heuristic Meaningfulness Classification**: Filters trivial noise and tags change categories (`PRICING_CHANGE`, `FEATURE_RELEASE`, `POSITIONING`, `DEPRECATION`, `OTHER`).
- **LangGraph Agentic Intelligence**: Orchestrated stateful graph executing Context Research, Impact Analysis, and Critic Verification.
- **Strict Evidence Grounding**: Calculates Evidence Grounding Accuracy ($EGA \ge 85\%$) and maps verbatim snapshot quotes with exact character offsets (`char_offset_start`, `char_offset_end`).
- **Hallucination Prevention**: Automatically downgrades or rejects ungrounded claims, ensuring proposals cite only verified evidence.
- **Structured Proposal Generator**: Synthesizes executive project counter-proposals adhering to a strict 7-section document standard.
- **Interactive Modern Frontend**: React 19 + Vite UI featuring real-time diff viewers, an "Analyze with AI" trigger, live EGA badges, and a Markdown proposal editor.
- **Zero-Paid-API Mandate**: Operates seamlessly with free/open-source LLMs (Groq, Gemini Free Tier, Ollama) and includes a deterministic mock adapter for offline testing.

---

## Agentic Workflow (LangGraph)

The system orchestrates competitive intelligence extraction using **LangGraph**:

```mermaid
flowchart TD
    A[Start: Change Record] --> B[Context Researcher Node]
    B --> C[Impact Analyzer Node]
    C --> D[Critic / Verifier Node]
    D -->|EGA < 85% & Retries Left| C
    D -->|EGA >= 85% or Max Retries| E[Persist IntelligenceFinding & EvidenceQuotes]
    E --> F[Optional: Proposal Engine]
    F --> G[End: 7-Section Counter-Proposal]
```

### Agent Nodes & Responsibilities

| Node | Responsibility | Output Artifacts |
|---|---|---|
| **Context Researcher** | Analyzes candidate diff in the context of the clean snapshot text; identifies factual claims and candidate quotes. | `factual_summary`, `extracted_quotes` |
| **Impact Analyzer** | Cross-references observed changes against the workspace's product positioning, value proposition, and strategic focus. | `title`, `category`, `impact_analysis`, `recommended_action` |
| **Critic / Verifier** | Verifies candidate quotes against snapshot text, maps character offsets, computes EGA %, and enforces downgrade/rejection thresholds. | `verified_quotes`, `grounding_score`, `verification_status`, `confidence_level` |
| **Proposal Generator** | Synthesizes verified findings into an executive-ready project proposal enforcing the 7-section standard and evidence quote attribution. | 7-section Markdown Proposal |

---

## System Architecture

```text
┌────────────────────────────────────────────────────────┐
│            Frontend (React 19 + Vite + Tailwind)       │
│  - Changes & Diff Viewer       - Findings Feed (EGA)   │
│  - AI Analysis Triggers        - Proposal Editor       │
└───────────────────────────┬────────────────────────────┘
                            │ REST / JSON (JWT Auth)
                            ▼
┌────────────────────────────────────────────────────────┐
│                 FastAPI Backend API                    │
│  - /auth, /workspaces, /competitors, /sources          │
│  - /scans, /changes, /findings, /proposals             │
└─────────────┬──────────────────────────────┬───────────┘
              │                              │
              ▼                              ▼
┌───────────────────────────┐  ┌───────────────────────────┐
│     SQLAlchemy 2.0 ORM    │  │   LangGraph Agent Engine  │
│  - SQLite (Local Dev/Test)│  │  - Context Researcher     │
│  - PostgreSQL (Production)│  │  - Impact Analyzer        │
└───────────────────────────┘  │  - Critic / Verifier      │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   LLM Provider Adapter    │
                               │  - Groq / Gemini / Ollama │
                               │  - Deterministic Mock     │
                               └───────────────────────────┘
```

### Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Uvicorn
- **Agent Orchestration**: LangGraph, LangChain Core, LangChain Community
- **Frontend**: React 19, Vite 8, Lucide React, React Router v7
- **Database**: SQLite (local development and automated testing) or PostgreSQL (production)
- **Ingestion & Diff Engine**: HTTPX, BeautifulSoup4, Feedparser, ElementTree, Myers unified diff

---

## Proposal Generator (7-Section Standard)

The proposal engine synthesizes verified competitor moves into an executive-ready counter-proposal. The output strictly enforces the following seven sections as Markdown H2 headers:

1. `## 1. Problem / Opportunity` — Commercial urgency and market shift.
2. `## 2. Competitor Change` — Verified competitor adjustments and categorization.
3. `## 3. Evidence` — Verbatim snapshot excerpts with source links and timestamps.
4. `## 4. Strategic Impact` — Implications for customer retention and pipeline velocity.
5. `## 5. Proposed Response` — Recommended strategic, technical, or commercial countermeasure.
6. `## 6. Suggested Features/Work` — Phased action plan (Immediate Parity, Core Differentiators, GTM).
7. `## 7. Expected Value` — Expected ROI, churn reduction, and strategic alignment.

> **Hallucination Guard**: The proposal API strictly bars any unverified or rejected finding (`verification_status != VERIFIED`).

---

## Repository Structure

```text
TradeCraft/
├── backend/
│   ├── app/
│   │   ├── adapters/          # Ingestion adapters (HTML, RSS/Atom)
│   │   ├── classifiers/       # Meaningfulness and noise classification
│   │   ├── core/              # Config (Settings), JWT security
│   │   ├── db/                # Database engine and session setup
│   │   ├── diff/              # Myers diff engine and change hashing
│   │   ├── models/            # SQLAlchemy ORM entities (Finding, Proposal, etc.)
│   │   ├── routers/           # FastAPI REST endpoints
│   │   ├── schemas/           # Pydantic v2 request/response models
│   │   └── services/
│   │       ├── agents/        # LangGraph StateGraph, nodes & LLM factory
│   │       ├── proposal_engine/ # 7-section proposal synthesis engine
│   │       ├── scan_service.py # Concurrent source scanning & pipeline trigger
│   │       └── change_service.py # Change detection & classification
│   ├── tests/                 # Comprehensive test suite (210 passing tests)
│   ├── main.py                # FastAPI entry point
│   └── requirements.txt       # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/        # UI components, DiffViewer, ChangeCard
│   │   ├── pages/             # Dashboard, Findings, Proposal, Competitors
│   │   ├── services/          # API client for backend communication
│   │   └── App.jsx            # Application root and route registration
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── DEVELOPMENT_JOURNEY.md # Technical challenges, root causes & resolutions
│   └── architecture.md        # Architecture specification
├── README.md
└── .env.example
```

---

## Setup & Running Guide

### 1. Environment Configuration

Create `.env` in the `backend/` directory:

```ini
# Application Settings
PROJECT_NAME="TradeCraft API"
VERSION="0.3.0"

# Security
JWT_SECRET="your-secure-jwt-secret-key-change-in-prod"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Configuration
# Leave empty for SQLite fallback (zero configuration needed), or specify PostgreSQL:
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/tradecraft"

# LLM Configuration (Zero-Paid API Mandate)
# Options: "mock" (offline/tests), "groq", "gemini", "ollama"
LLM_PROVIDER="mock"
LLM_MODEL_NAME="llama-3.3-70b-versatile"
GROQ_API_KEY=""
GEMINI_API_KEY=""
OLLAMA_BASE_URL="http://localhost:11434"
```

### 2. Backend Setup & Startup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --port 8001 --reload
```

- **API Base URL**: `http://localhost:8001`
- **Interactive Swagger Docs**: `http://localhost:8001/docs`
- **Health Check**: `GET http://localhost:8001/health`

### 3. Frontend Setup & Startup

```bash
cd frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```

- **Application URL**: `http://localhost:5173` (or `http://localhost:5174`)

---

## Running the Integrated Pipeline

### Automated Execution (via Scans)
1. Add a competitor and configure a source URL (e.g., a competitor pricing or changelog page).
2. Trigger a scan (`POST /workspaces/{id}/scan` or click **"Run Scan"** in the UI).
3. If the page content has changed since the previous snapshot, the system computes the unified diff.
4. If classified as **meaningful**, `scan_service.py` automatically passes the change to the LangGraph agent pipeline.
5. The pipeline executes `Context Researcher -> Impact Analyzer -> Critic Verifier`, persisting an `IntelligenceFinding` with evidence quotes.

### Manual On-Demand Execution
To trigger AI analysis on any detected change via API:
```bash
POST /changes/{change_id}/analyze
Authorization: Bearer <your_token>
```
Or on the web UI: navigate to **Findings**, click **"Analyze with AI"** on any change card, and inspect the resulting EGA score and grounded quotes.

### Proposal Generation
1. In the web UI, navigate to **Proposals**.
2. Click **"New Proposal"**, provide a title and target goal, and select the verified findings to include.
3. Click **"Generate Proposal"** to synthesize the 7-section executive counter-proposal.
4. Review, edit the markdown, or toggle status between `DRAFT` and `FINALIZED`.

---

## Running Automated Tests

The test suite covers source parsing, change hashing, diff computation, security isolation, the LangGraph agent workflow, evidence grounding, and proposal generation:

```bash
cd backend
source venv/bin/activate # or .\venv\Scripts\activate on Windows

# Run the complete test suite (210 tests)
pytest -v

# Run the LangGraph integration tests specifically
pytest tests/test_agent_pipeline_integration.py -v
```

All 210 tests pass deterministically without network dependencies using the mock LLM adapter.

---

## Project Status

| Component | Status |
|---|---|
| User Authentication & JWT Security | ✅ Completed |
| Workspace, Competitor & Source Management | ✅ Completed |
| Ingestion Adapters (HTML & RSS/Atom) | ✅ Completed |
| Immutable Snapshot Engine & Myers Diff | ✅ Completed |
| Meaningfulness Classification & Noise Filter | ✅ Completed |
| LangGraph Agent Pipeline (Researcher, Analyzer, Critic) | ✅ Completed |
| Evidence Grounding Accuracy ($EGA \ge 85\%$) & Char Offsets | ✅ Completed |
| 7-Section Strategic Counter-Proposal Synthesis | ✅ Completed |
| React 19 Frontend with Findings & Proposal Editor | ✅ Completed |
| 210 Automated Pytest Tests | ✅ 100% Passing |
