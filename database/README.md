# TradeCraft Database

## Technology

**PostgreSQL**

## Phase 1 Status

The database layer is in its foundation stage.

Currently implemented:
- PostgreSQL connection configuration (via env vars)
- Basic reachability check (used by `/health`)

Not yet implemented:
- Full schema (planned for Phase 2)
- Migrations
- ORM models

## Setup

### 1. Install PostgreSQL

If not already installed: https://www.postgresql.org/download/

### 2. Create the database

```bash
psql -U postgres
```

```sql
CREATE DATABASE tradecraft;
\q
```

### 3. Configure environment variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tradecraft
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
```

### 4. (Optional) Run the Phase 1 schema placeholder

```bash
psql -U your_postgres_username -d tradecraft -f database/schema.sql
```

This only enables the `uuid-ossp` extension for now.

## Planned Schema (Phase 2)

The full schema will cover:

| Table           | Purpose                              |
|-----------------|--------------------------------------|
| users           | User accounts                        |
| workspaces      | Product / project context            |
| competitors     | Competitor profiles                  |
| sources         | Configured public URLs               |
| snapshots       | Fetched source content history       |
| analysis_runs   | Individual scan executions           |
| changes         | Detected source changes              |
| findings        | Validated competitive intelligence   |
| evidence        | Source-backed supporting evidence    |
| proposals       | Generated project proposals          |
