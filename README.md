# TradeCraft

## AI Competitive Intelligence & Proposal Generator

An agentic competitive-intelligence platform that monitors competitor changes, investigates their significance, verifies supporting evidence, and generates actionable insights and project proposals.

## Overview

Teams often monitor competitors manually across pricing pages, product pages, changelogs, blogs, public repositories, and announcements.

Existing change-monitoring tools can identify that a page changed, but they do not necessarily explain:

- What changed?
- Why does it matter?
- What evidence supports the conclusion?
- What should we consider doing next?

TradeCraft addresses that gap by combining source monitoring, change detection, agentic research, impact analysis, verification, and proposal generation into a single workflow.

### Core Workflow

```text
What Changed?
      ↓
Why Does It Matter?
      ↓
What Evidence Supports It?
      ↓
What Should We Consider Doing Next?
      ↓
Generate a Project Proposal
```

## Key Features

- User authentication and workspace management
- Competitor management
- Public source configuration
- On-demand competitor scans
- Source snapshot storage
- Deterministic change detection
- Meaningfulness classification
- Context research
- Impact analysis
- Evidence verification
- Confidence and verification status
- Findings dashboard
- Scan history
- Evidence-backed recommendations
- Structured project proposal generation
- Editable proposal output

## Agentic Workflow

The system uses LangGraph as the orchestration layer.

```text
START
  │
  ▼
Collect
  │
  ▼
Detect Changes
  │
  ▼
Classify
  │
  ├──────── No meaningful change ───────► END
  │
  ▼
Research
  │
  ▼
Impact Analysis
  │
  ▼
Verify
  │
  ├──────── Reject / insufficient evidence ─► END
  │
  ▼
Report
  │
  ▼
Optional Proposal Generation
  │
  ▼
END
```

### Agent Components

| Component | Responsibility |
|---|---|
| Collector | Fetch configured public sources and latest snapshots |
| Change Detector | Determine what changed since the previous snapshot |
| Change Classifier | Filter trivial changes and classify significance |
| Context Researcher | Gather additional supporting context |
| Impact Analyst | Relate changes to the user's project/product context |
| Critic / Verifier | Challenge unsupported claims and assess evidence |
| Report Generator | Produce facts, interpretation, evidence, confidence, and recommendation |
| Proposal Generator | Convert validated findings into a structured project proposal |

## System Architecture

The MVP uses a simple full-stack architecture:

```text
┌───────────────────────┐
│      Next.js UI       │
│  Dashboard / Findings │
│  Proposal Editor      │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│      FastAPI API      │
│ Auth / REST / Control │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│      LangGraph        │
│   Agentic Workflow    │
└───────────┬───────────┘
            │
      ┌─────┴─────┐
      ▼           ▼
┌───────────┐ ┌────────────────┐
│PostgreSQL │ │ Source Adapters│
│           │ │ Web / RSS / GH │
└───────────┘ └────────────────┘
```

### Technology Stack

**Frontend**
- Next.js
- React

**Backend**
- Python
- FastAPI
- LangGraph

**Database**
- PostgreSQL

**Source ingestion**
- HTTP fetching
- HTML parsing
- RSS/Atom parsing
- Optional public GitHub sources

**AI layer**
- Free/open-source or free-tier models
- Provider-independent LLM adapter

## MVP Scope

The MVP is intentionally limited to a small number of competitors and public sources.

The system should support:

- 2–5 competitors per workspace
- A small number of configured public sources per competitor
- Manual `Run Scan`
- Source snapshots
- Change detection
- Meaningfulness classification
- Context research
- Impact analysis
- Evidence verification
- Findings and recommendations
- Proposal generation from validated findings

The MVP does **not** aim to be a general-purpose web crawler or large-scale monitoring platform.

## Evidence and Hallucination Controls

A major design principle of this project is that AI-generated conclusions must not be presented as facts.

Every finding should distinguish between:

```text
FACTS
     ↓
Observed from collected evidence

INTERPRETATION
     ↓
AI-generated analysis of what the change may mean

RECOMMENDATION
     ↓
Suggested next step based on the evidence and interpretation
```

The system should:

- Store source URLs and fetch timestamps
- Require source-backed evidence for findings
- Track confidence and verification status
- Reject or mark findings as unconfirmed when evidence is insufficient
- Surface contradictory evidence
- Avoid inventing competitor prices, features, dates, or announcements

## Proposal Generator

Validated competitive findings can be converted into a structured project proposal.

The proposal may contain:

- Project title
- Background / market context
- Problem statement
- Target users
- Observed evidence
- Proposed solution
- Key features
- Agentic AI role
- Functional requirements
- High-level architecture
- Suggested technology stack
- MVP scope
- Future scope
- Risks and assumptions
- Evaluation plan
- Expected outcome

The proposal should clearly distinguish evidence-derived facts from AI-generated interpretation and recommendations.

## Project Roadmap

### Phase 1 — Project Foundation
- Frontend scaffold
- Backend scaffold
- Database setup
- Architecture documentation
- Health checks

### Phase 2 — Core Management
- Authentication
- Workspace creation
- Competitor management
- Source configuration

### Phase 3 — Data Collection
- Source adapters
- Snapshot storage
- Fetching and parsing

### Phase 4 — Change Detection
- Deterministic comparison
- Change hashing
- Meaningfulness filtering

### Phase 5 — Agentic Intelligence
- LangGraph workflow
- Context research
- Impact analysis
- Verification
- Report generation

### Phase 6 — Dashboard
- Findings interface
- Evidence view
- Scan history
- Filtering and status management

### Phase 7 — Proposal Generation
- Proposal generation
- Proposal editing
- Export / copy workflow

### Phase 8 — Evaluation & Testing
- Unit tests
- Integration tests
- Agent tests
- End-to-end testing
- Evaluation fixtures and benchmarks

### Phase 9 — Polish & Deployment
- UI refinement
- Optional scheduling
- Deployment

## Evaluation

The system will be evaluated at four levels:

| Area | Evaluation |
|---|---|
| Change Detection | Precision / recall using controlled source changes |
| Meaningfulness Classification | Comparison against manually labelled data |
| Evidence Correctness | Verify that evidence supports stated facts |
| Proposal Quality | Human evaluation of grounding, usefulness, completeness, and actionability |

## Testing

Testing will cover:

- Source parsers
- Change hashing
- Candidate filtering
- Data models
- API validation
- Database + API integration
- LangGraph agent behavior
- End-to-end workflow
- Source failures
- LLM failures
- Malformed model output
- Duplicate findings
- Insufficient evidence

## Cost Constraint

The project is designed to operate without a paid LLM dependency.

The architecture will:

- Keep LLM calls behind a single adapter
- Allow provider/model configuration through environment variables
- Prefer deterministic processing before LLM calls
- Cache analysis where practical
- Gracefully handle free-provider rate limits
- Continue with non-AI checks when an LLM call fails

## Repository Structure

```text
.
├── frontend/
├── backend/
├── database/
├── docs/
├── .env.example
├── .gitignore
└── README.md
```

## Project Status

**Current stage: Phase 1 — Project Foundation**

The current development focus is establishing the project architecture, frontend/backend scaffolding, database setup, and basic health checks.

## Project Positioning

> **An agentic competitive-intelligence platform that monitors competitor changes, investigates their significance, verifies evidence, and generates actionable insights and project proposals.**
