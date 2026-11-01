# TradeCraft Development Journey: LangGraph Pipeline Integration

This document records the technical challenges encountered, root-cause analyses, attempted solutions, final resolutions, and engineering lessons learned during the integration of the independently developed LangGraph competitive intelligence pipeline into TradeCraft.

---

## Technical Challenge 1: Resolving Top-Level Database Driver Import in Local / Testing Environments

### 1. Implementation Goal
We aimed to run and verify the TradeCraft FastAPI backend (`backend/main.py`) and execute test suites under a standard Python 3.13 environment using SQLite for local development and CI testing.

### 2. Problem Encountered
When attempting to import `main.py` or execute Pytest, the Python interpreter immediately crashed with:
```text
ModuleNotFoundError: No module named 'psycopg2'
at backend/db.py:19 in <module>
    import psycopg2
```

### 3. Why the Problem Occurred
In `backend/main.py`, the health check initialization imports `from db import check_db_connection`. In `backend/db.py`, `import psycopg2` was placed as an unconditional top-level module import. In environments configured for SQLite (or developer machines without PostgreSQL C-bindings installed), this prevented the entire FastAPI application and test suite from loading, even though `app/db/database.py` was already architected to support SQLite fallback.

### 4. What Was Initially Investigated
We checked whether psycopg2 could be installed or if binary wheels were cached. However, for a college software engineering project and portable CI environments, requiring compiled PostgreSQL binaries just to boot an application that uses SQLite locally creates unnecessary deployment friction.

### 5. Final Resolution
We made the import in `backend/db.py` defensive:
```python
try:
    import psycopg2
except ImportError:
    psycopg2 = None
```
Inside `check_db_connection()`, if `psycopg2 is None`, it safely returns `(False, "psycopg2 is not installed (running in SQLite/lightweight mode)")` instead of crashing the interpreter. This maintains 100% backward compatibility with PostgreSQL production configurations while enabling instant, zero-friction startup in local SQLite development.

### 6. Lessons Learned
Top-level database driver imports couple an application to a specific backend dialect at parse time. Optional or health-check-specific database drivers should always be guarded or imported lazily, particularly when the core application supports multiple database backends via SQLAlchemy.

---

## Technical Challenge 2: Harmonizing Data Models and Session Dialects Between Async Pipeline and Synchronous SQLAlchemy Core

### 1. Implementation Goal
Integrate `IntelligenceFinding`, `EvidenceQuote`, and `Proposal` database entities into TradeCraft's existing SQLAlchemy ORM architecture.

### 2. Problem Encountered
The independently developed LangGraph pipeline used `AsyncSession` with an internal `candidate_diff_id` foreign key and custom async table definitions. Meanwhile, TradeCraft's core architecture uses synchronous SQLAlchemy 2.0 (`Session = sessionmaker(...)`, `db: Session = Depends(get_db)`) with `Change` entities (`changes.id`, `current_snapshot_id`, `diff_unified`). Attempting to force TradeCraft into an async session model would break over 206 passing unit, API, and adversarial security tests.

### 3. Why the Problem Occurred
The two modules were developed independently: TradeCraft prioritized robust synchronous REST API endpoints and transactional stability, whereas the experimental LangGraph pipeline experimented with asyncio constructs. Additionally, foreign key naming differed (`candidate_diff_id` vs `change_id`).

### 4. What Was Attempted
We considered maintaining two separate database sessions (one async for the pipeline and one sync for TradeCraft). However, this would prevent atomic transactions, introduce dual connection pools, and create potential SQLite lock contention during automated tests.

### 5. Final Resolution
We unified the data models directly on TradeCraft's synchronous `Base`:
1. `IntelligenceFinding` references `changes.id` via `change_id`, and exposes a `@property candidate_diff_id` for transparent compatibility with pipeline nodes.
2. `Proposal` was integrated with `workspaces.id` and standard `ProposalStatus` enum.
3. Bidirectional relationships were established on `Workspace`, `Change`, and `Snapshot`.
4. Pydantic schemas were implemented in `app/schemas/finding.py` and `app/schemas/proposal.py`, supporting full response serialization with evidence grounding.

### 6. Lessons Learned
When integrating an independently developed AI pipeline into an existing enterprise codebase, align the pipeline to the host application's database session lifecycle rather than forcing an asynchronous architectural rewrite of the host system.

---

## Technical Challenge 3: Punctuation Normalization Disparity in Syndication Feed Parsing

### 1. Implementation Goal
Ensure syndication feed normalization produces deterministic, clean text across all feed types (RSS 2.0, Atom 1.0) and parser configurations.

### 2. Problem Encountered
In `test_adapters.py::test_atom_feed_normalization`, the test asserted:
```text
AssertionError: assert 'Summary: Patched a critical vulnerability in API authentication.' in '...Summary: Patched a critical vulnerability in API authentication .\n---'
```
An unexpected whitespace appeared directly preceding punctuation (`"API authentication ."`).

### 3. Why the Problem Occurred
When `feedparser` is available, summary HTML containing tags like `<a href="#">API authentication</a>.` was cleaned by regex replacing `<[^>]+>` with a single space `" "`. Because the closing anchor tag was adjacent to punctuation, replacing `</a>` with `" "` left a floating space right before the period. When the fallback `ElementTree` was used without `feedparser`, `itertext()` extracted inner text without inserting spaces around tags.

### 4. What Was Attempted
One option was to change the test assertion, but that would weaken the normalization contract. The proper fix was to ensure regex normalization cleans spaces preceding punctuation.

### 5. Final Resolution
We updated the summary normalization pipeline in `app/adapters/rss_adapter.py`:
```python
clean_summary = re.sub(r"<[^>]+>", " ", e.get("summary", ""))
clean_summary = clean_summary.replace("\xa0", " ")
clean_summary = re.sub(r"\s+([.,!?;:])", r"\1", clean_summary)
clean_summary = re.sub(r"\s+", " ", clean_summary).strip()
```
This cleanly strips extraneous whitespace before punctuation marks, making the normalization strictly deterministic across both parser paths.

### 6. Lessons Learned
HTML tag stripping via regex should always normalize whitespace relative to punctuation boundaries to avoid syntactically malformed sentences in downstream diffs and LLM context windows.

---
