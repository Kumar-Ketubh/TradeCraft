# TradeCraft Backend

FastAPI + LangGraph agentic backend powering **TradeCraft**. Connects to Supabase PostgreSQL, executes multi-node agentic pipelines, enforces evidence grounding, and synthesizes strategic project proposals.

---

## 🚀 Live Production Deployment

- **Base API URL**: **[https://tradecraft-xax5.onrender.com](https://tradecraft-xax5.onrender.com)**
- **Interactive Swagger Docs**: **[https://tradecraft-xax5.onrender.com/docs](https://tradecraft-xax5.onrender.com/docs)**
- **Health Check**: **[https://tradecraft-xax5.onrender.com/health](https://tradecraft-xax5.onrender.com/health)**
- **Frontend App**: **[https://trade-craft-sage.vercel.app](https://trade-craft-sage.vercel.app)**

---

## Core Capabilities

- **Modular REST APIs**: Clean domain separation across `/auth`, `/workspaces`, `/competitors`, `/sources`, `/scans`, `/changes`, `/findings`, and `/proposals`.
- **Cloud Database (Supabase PostgreSQL)**: 10 relational tables provisioned with connection pooling, SSL enforcement, and IPv4 Supavisor support.
- **LangGraph Agent Workflow**: Stateful 3-node graph (`Context Researcher` → `Impact Analyzer` → `Critic / Verifier`) with automatic retry loops and EGA enforcement ($EGA \ge 85\%$).
- **Deterministic Diff Engine**: Myers diff algorithm with SHA-256 change hashing and meaningfulness classification.
- **Strategic Proposal Generator**: 7-Section executive counter-proposals citing only verified evidence.

---

## Local Setup

### 1. Virtual Environment & Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Environment Variables

Create `.env` in `backend/`:

```ini
PROJECT_NAME="TradeCraft API"
VERSION="0.3.0"
JWT_SECRET="tradecraft-secret-jwt-key"
DATABASE_URL="postgresql://postgres.ptalxyofynhiszkisuay:adityakochar2006@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"
LLM_PROVIDER="mock" # or "gemini", "groq", "ollama"
GEMINI_API_KEY=""
```

### 3. Start Local Server

```bash
uvicorn main:app --port 8001 --reload
```

---

## Automated Tests

Run the full 210-test suite:

```bash
pytest -v
```
All 210 tests pass deterministically without network dependencies.
