# TradeCraft Backend

## Technology Status

> **The final backend technology (FastAPI vs Node.js) is TBD.**
>
> FastAPI is used here as a temporary scaffold to unblock frontend development
> and provide health checks. The final decision will be documented in
> `docs/architecture.md` once the team evaluates both options.

## Phase 1 — What is implemented

- `GET /health` — returns backend status and PostgreSQL reachability

## What is NOT implemented yet

- Authentication
- Competitor management APIs
- Source configuration APIs
- Scan execution
- Change detection
- LangGraph / LLM integration

These belong to later phases.

## Setup

### 1. Create a virtual environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 4. Start the server

```bash
uvicorn main:app --port 8001 --reload
```

The server runs at: `http://localhost:8000`

### 5. Test the health endpoint

```bash
curl http://localhost:8000/health
```

Expected response (with DB connected):

```json
{
  "backend": "ok",
  "database": "ok",
  "database_message": "Connected",
  "ai_workflow": "not_connected",
  "phase": "Phase 1 — Project Foundation"
}
```

If the database is not configured yet, `database` will be `"error"` — this is expected.

## API Docs

FastAPI auto-generates interactive docs at:

- `http://localhost:8001/docs` (Swagger UI)
- `http://localhost:8001/redoc`
