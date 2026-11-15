# TradeCraft — Core Engineering & Logical Problems Faced

A technical breakdown of the core algorithmic, architectural, and data-flow problems encountered while building the **TradeCraft AI Competitive Intelligence & Proposal Engine**, how each was diagnosed under the hood, and how it was solved.

---

## Table of Contents
1. [The Evidence Grounding & Exact Verbatim Citation Problem (EGA)](#1-the-evidence-grounding--exact-verbatim-citation-problem-ega)
2. [The Ephemeral DOM Noise vs. Substantive Change Problem (Myers Diff & Classification)](#2-the-ephemeral-dom-noise-vs-substantive-change-problem-myers-diff--classification)
3. [The Multi-Agent State Synchronization & Verification Retry Loop](#3-the-multi-agent-state-synchronization--verification-retry-loop)
4. [The Synchronous Database Transaction vs. Asynchronous Agent Pipeline Mismatch](#4-the-synchronous-database-transaction-vs-asynchronous-agent-pipeline-mismatch)
5. [The Feed Ingestion Normalization & Punctuation Integrity Problem](#5-the-feed-ingestion-normalization--punctuation-integrity-problem)
6. [The Multi-Tenant Relational Isolation & Ownership Enforcement](#6-the-multi-tenant-relational-isolation--ownership-enforcement)
7. [The Deterministic Testing Mandate for Non-Deterministic AI Pipelines](#7-the-deterministic-testing-mandate-for-non-deterministic-ai-pipelines)
8. [The 7-Section Strategic Proposal Synthesis & Strict Schema Validation](#8-the-7-section-strategic-proposal-synthesis--strict-schema-validation)
9. [The Long-Running Agent Scan Pipeline vs. HTTP Request Lifecycles](#9-the-long-running-agent-scan-pipeline-vs-http-request-lifecycles)

---

## 1. The Evidence Grounding & Exact Verbatim Citation Problem (EGA)

### The Problem
When Large Language Models (LLMs) are asked to summarize competitor updates, they naturally paraphrase claims or invent plausible-sounding details that never appeared on the competitor's website. In competitive intelligence, basing a business strategy on a misquoted price, altered feature description, or hallucinated claim can lead to disastrous executive decisions.

### Why It Happened (Under the Hood)
LLMs operate as probabilistic token predictors optimized for semantic fluency rather than strict literal accuracy. When given a context window of raw website text, an LLM often compresses or rephrases statements (e.g. turning *"Plans start at \$49/mo billed annually"* into *"They dropped their base tier to forty-nine dollars"*). Because the text is rephrased, standard string matching cannot verify if the competitor actually made that claim or if the model invented the nuance.

### How We Solved It
We designed an adversarial verification architecture inside our **LangGraph** multi-agent pipeline:
1. **Verbatim Quote Mandate**: The `Context Researcher` node is strictly instructed to extract exact, verbatim candidate quote substrings from the clean snapshot text alongside its factual summary.
2. **The Critic / Verifier Node (The Guardrail)**: Rather than trusting the LLM's quotes, the Critic node performs a deterministic, code-level search across the raw snapshot text stored in the database:
   - For every candidate quote, it verifies whether the substring exists verbatim.
   - If found, it computes the exact start and end character offsets (`char_offset_start` to `char_offset_end`) within the raw text.
3. **Evidence Grounding Accuracy (EGA) Metric**:
   $$\text{EGA} = \left(\frac{\text{Number of Verified Quotes}}{\text{Total Candidate Quotes}}\right) \times 100\%$$
4. **Enforcement Threshold**: If $\text{EGA} < 85\%$, the finding is automatically flagged as ungrounded and downgraded or rejected.
5. **Proposal Firewall**: The proposal engine enforces a hard database filter: any finding that does not hold a `VERIFIED` status is strictly barred from being used in executive proposals.

### Key Takeaway
Never rely on an LLM to self-verify its own output. Pair generative models with deterministic, code-level validators that calculate exact character coordinates in source documents before accepting claims as factual.

---

## 2. The Ephemeral DOM Noise vs. Substantive Change Problem (Myers Diff & Classification)

### The Problem
During initial end-to-end tests, running an automated scan against live websites flooded the database with dozens of "Competitor Changes" every single hour, even when the competitor had not made any real product, pricing, or strategic adjustments.

### Why It Happened (Under the Hood)
Modern websites are highly dynamic. Even when static content remains identical, the HTML DOM changes on every request:
- Rotating advertising banners and dynamic analytics tracking scripts.
- Session IDs, anti-CSRF tokens, and cache-busting query parameters.
- Server-rendered relative timestamps (e.g. *"Updated 3 minutes ago"* $\rightarrow$ *"Updated 4 minutes ago"*).
- Footer copyright year increments (`© 2025` $\rightarrow$ `© 2026`).

If a monitoring system naively computes a cryptographic SHA-256 hash or runs a raw diff on incoming HTML, every single page load looks like a brand-new change, triggering unnecessary database writes and wasting expensive AI pipeline invocations.

### How We Solved It
We engineered a two-stage noise reduction pipeline:
1. **DOM Sanitization (`HtmlAdapter`)**:
   - Parses the HTML DOM using BeautifulSoup and strips out non-content elements: `<script>`, `<style>`, `<noscript>`, `<nav>`, `<footer>`, `<header>`, cookie banners, and modal overlays.
   - Decodes HTML entities and normalizes whitespace into single-space delimiters before generating the snapshot hash.
2. **Deterministic Heuristic Meaningfulness Classifier**:
   - Computes line-by-line diffs using the **Myers unified diff algorithm**.
   - Evaluates the diff chunks against a weighted heuristic ruleset: checks for business-critical indicators such as currency symbols (`$`, `€`, `£`), pricing keywords (`per user`, `billed annually`, `enterprise tier`), and product lifecycle verbs (`deprecated`, `introducing`, `new feature`, `discontinued`).
   - If a diff contains only cosmetic updates, date changes, or formatting adjustments, it is tagged as `NOISE` and immediately dropped from the AI pipeline.
   - Significant changes are automatically classified into domain categories: `PRICING_CHANGE`, `FEATURE_RELEASE`, `POSITIONING`, or `DEPRECATION`.

### Key Takeaway
Effective change monitoring is fundamentally a noise-filtering problem. Raw diffing without structural DOM sanitization and heuristic classification produces overwhelming noise that drowns out genuine strategic signals.

---

## 3. The Multi-Agent State Synchronization & Verification Retry Loop

### The Problem
In early iterations of our agentic workflow, when the Critic agent rejected a finding because the extracted quotes could not be verified in the source text, the entire pipeline would either crash, terminate with an empty result, or enter an infinite loop trying to re-analyze the same broken text.

### Why It Happened (Under the Hood)
In multi-agent systems, agents must pass state between each other. Our workflow involves three specialized roles:
$$\text{Context Researcher} \longrightarrow \text{Impact Analyzer} \longrightarrow \text{Critic / Verifier}$$
If the Critic rejects a candidate quote, simply throwing an error wastes the compute already spent by the Researcher and Analyzer. Conversely, naively routing the graph back to the beginning without passing critique feedback causes the upstream agent to generate the exact same hallucinated quote again, causing an infinite cycle.

### How We Solved It
We modeled the workflow as a formal **LangGraph StateGraph** with structured memory and bounded conditional routing:
1. **Typed Agent State (`AgentState`)**: Built a structured state dictionary that flows across all nodes, carrying the raw snapshot text, clean diff, extracted quotes, candidate findings, critique notes, and an explicit `retry_count`.
2. **Critique Feedback Injection**: When the Critic calculates an $\text{EGA} < 85\%$, it appends specific feedback into the state (e.g., *"Quote 'X' was not found verbatim in source text; re-extract from lines 12–24"*).
3. **Bounded Conditional Edges**: We added a conditional routing edge after the Critic node:
   - If $\text{EGA} \ge 85\%$, route to the persistence node (`save_finding`).
   - If $\text{EGA} < 85\%$ and `retry_count < max_retries` (default: 2), increment `retry_count` and route back to the `Impact Analyzer` with the critique feedback.
   - If `retry_count >= max_retries`, mark the finding as `REJECTED` or `DOWNGRADED` and terminate cleanly without infinite looping.

### Key Takeaway
Agentic workflows require explicit state machines with bounded retry limits and structured feedback channels. Without deterministic routing conditions, multi-agent loops easily degrade into infinite loops or silent failures.

---

## 4. The Synchronous Database Transaction vs. Asynchronous Agent Pipeline Mismatch

### The Problem
When integrating the LangGraph agent pipeline into TradeCraft's backend, background scans and test suites began deadlocking. Tests either froze indefinitely or threw errors:
```text
RuntimeError: Task <...> got Future <...> attached to a different loop
OperationalError: (sqlite3.OperationalError) database is locked
```

### Why It Happened (Under the Hood)
LangGraph and modern LLM frameworks are architected around Python's asynchronous event loop (`async def` with `asyncio`). However, TradeCraft's existing REST endpoints, multi-tenant permission layers, and 200+ unit test fixtures were built using synchronous SQLAlchemy sessions (`Session = sessionmaker()`).

When a synchronous FastAPI endpoint or test fixture attempted to run an async LangGraph graph using `asyncio.run()`, it spawned nested, competing event loops on worker threads. Because SQLite (used in automated testing) and PostgreSQL connection pools hold row-level or file-level locks during active transactions, having an asynchronous coroutine attempt to query the database while the parent synchronous thread held an open session caused immediate database deadlocks.

### How We Solved It
Instead of rewriting all 200+ tests and database models to be asynchronous, we synchronized the agent execution boundary:
1. Adapted the LangGraph pipeline execution so that graph nodes invoke synchronous tool wrappers.
2. Passed the caller's active database `Session` directly into the agent state.
3. Structured database writes so that the snapshot creation, diff generation, finding insertion, and evidence quote offset mapping all occur within the **same atomic database transaction**.
4. If an agent step fails, the caller's transaction cleanly rolls back, preventing orphaned findings or detached quotes.

### Key Takeaway
When introducing modern AI libraries into an existing production stack, adapt the AI wrapper to fit the application's transaction lifecycle—never rewrite working transactional infrastructure to satisfy an external library's async bias.

---

## 5. The Feed Ingestion Normalization & Punctuation Integrity Problem

### The Problem
In automated RSS feed tests, candidate quotes extracted from competitor changelogs and blogs repeatedly failed exact substring verification in the Critic agent, even though the text was visibly present on the competitor's page.

### Why It Happened (Under the Hood)
Competitor news feeds (RSS 2.0 and Atom 1.0) frequently wrap hyperlinks around key terms at the end of sentences:
```html
<p>Patched critical security <a href="/advisory">vulnerability</a>.</p>
```
When our HTML parser stripped the tags, it inserted a whitespace character for every closing tag to prevent adjacent words from colliding (e.g. `word1</a><a>word2` becoming `word1word2`). However, because the period was located immediately after the closing `</a>` tag, the cleaner inserted an artificial space between the word and the period:
```text
"Patched critical security vulnerability ."
```
While human readers overlook a floating space before a period, the Critic agent's substring search algorithm performs an exact, character-by-character comparison. Because the candidate quote had `"vulnerability ."` but the raw snapshot had `"vulnerability."`, the substring search failed, causing the Critic to reject legitimate quotes and lower the EGA score.

### How We Solved It
We added an automated regex post-processing filter to the sanitization pipeline:
```python
text = re.sub(r"\s+([.,!?;:])", r"\1", text)
```
This rule detects any whitespace preceding punctuation marks and binds the punctuation directly to the preceding word. This restored natural typography while ensuring 100% exact verbatim character alignment between parsed candidate quotes and the raw snapshot text.

### Key Takeaway
Data cleaning for AI verification requires typographic precision. In exact-match verification systems, minor whitespace inconsistencies around punctuation will break substring matching and trigger false hallucination rejections.

---

## 6. The Multi-Tenant Relational Isolation & Ownership Enforcement

### The Problem
TradeCraft is designed as a multi-tenant system where organizations manage sensitive competitor intelligence. In early endpoint designs, an authenticated user belonging to Workspace A could theoretically access or trigger scans on a competitor belonging to Workspace B simply by knowing or guessing the target ID (`competitor_id` or `change_id`).

### Why It Happened (Under the Hood)
Standard CRUD implementations often query entities directly by primary key:
```python
# Vulnerable pattern
competitor = db.query(Competitor).filter(Competitor.id == competitor_id).first()
```
While authentication checks verify *who* the user is (valid JWT token), they do not verify whether that user has authorization to access the specific requested resource. Because primary keys in relational databases are often sequential integers or guessable identifiers, querying solely by entity ID allows unauthorized cross-tenant data leaks (Insecure Direct Object References - IDOR).

### How We Solved It
We implemented strict **Relational Hierarchy Traversal Guards** across all database queries:
1. Every entity in TradeCraft belongs to a strict relational hierarchy:
   $$\text{User} \longrightarrow \text{WorkspaceMember} \longrightarrow \text{Workspace} \longrightarrow \text{Competitor} \longrightarrow \text{Source} \longrightarrow \text{ScanRun} \longrightarrow \text{Change} \longrightarrow \text{Finding}$$
2. Created a FastAPI dependency (`get_current_workspace`) that extracts the authenticated user from the JWT and validates their active workspace membership.
3. Every single query joins through the `Workspace` entity and filters by the authenticated `workspace_id`:
   ```python
   # Secure pattern
   competitor = db.query(Competitor).join(Workspace).filter(
       Competitor.id == competitor_id,
       Workspace.id == current_user_workspace_id
   ).first()
   ```
4. If an entity exists in the database but belongs to another tenant, the API returns a `404 Not Found` rather than a `403 Forbidden`, preventing attackers from enumerating the existence of other tenants' competitor IDs.

### Key Takeaway
Authentication is not authorization. In multi-tenant relational systems, every database query must explicitly join through the tenant ownership boundary rather than relying on global primary key lookups.

---

## 7. The Deterministic Testing Mandate for Non-Deterministic AI Pipelines

### The Problem
Running automated test suites (CI/CD) that depend on external LLM APIs (OpenAI, Gemini, Groq) creates fragile, non-deterministic builds. Tests frequently fail due to API rate limits, network latency, billing quotas, or slight variations in model responses.

### Why It Happened (Under the Hood)
Generative LLMs are inherently non-deterministic: setting `temperature=0` reduces randomness but does not guarantee identical token sequences across model revisions. Furthermore, unit testing a 210-test suite against live cloud APIs takes minutes, consumes costly API credits, and breaks completely when running in offline development environments.

### How We Solved It
We architected a **Zero-Paid-API Modular Factory Pattern** (`LLMProviderFactory`):
1. **The Deterministic Mock Adapter (`MockLLM`)**: Built an offline adapter that simulates LLM reasoning deterministically without network calls.
   - Parses the candidate diff using deterministic keyword extraction.
   - Extracts real substrings from the actual snapshot text, guaranteeing valid character offsets.
   - Generates predictable, structured findings with reproducible EGA scores ($\ge 90\%$) and complete 7-section proposal documents.
2. **Pluggable Real LLM Adapters**: Created seamless runtime adapters for live free-tier providers (Google Gemini 1.5 Flash, Groq Llama-3.3, and local Ollama) that adhere to the exact same interface.
3. **Test Suite Independence**: Configured the automated test suite (`pytest`) to run exclusively against the deterministic mock model. All 210 tests execute in seconds, run fully offline, and produce 100% reproducible results.

### Key Takeaway
Never couple continuous integration test suites to live, non-deterministic third-party AI APIs. Always design a deterministic mock provider that simulates domain logic predictably for rapid, offline testing.

---

## 8. The 7-Section Strategic Proposal Synthesis & Strict Schema Validation

### The Problem
When asked to generate executive counter-proposals based on competitor findings, raw language models frequently produced unstructured essays, missed critical business analysis sections, or omitted concrete feature implementation roadmaps.

### Why It Happened (Under the Hood)
Unconstrained LLMs treat document generation as open-ended text completion. Without structural boundaries, the model prioritizes whatever section it weights most heavily, often producing an extensive problem statement while completely skipping commercial countermeasures or engineering timelines. For executive decision-makers, inconsistent proposal formats make cross-competitor evaluation impossible.

### How We Solved It
We engineered the **Proposal Engine** (`backend/app/services/proposal_engine/`) with structural schema enforcement:
1. **The 7-Section Document Standard**: Mandated that every generated proposal strictly adhere to exactly seven Markdown H2 sections:
   - `## 1. Problem / Opportunity` — Commercial urgency and market shift.
   - `## 2. Competitor Change` — Verified competitor updates and categorization.
   - `## 3. Evidence` — Verbatim snapshot excerpts with offset-backed citations.
   - `## 4. Strategic Impact` — Impact on retention, sales pipeline, and market positioning.
   - `## 5. Proposed Response` — Recommended strategic countermeasure.
   - `## 6. Suggested Features/Work` — Phased roadmap (Immediate Parity, Differentiators, GTM).
   - `## 7. Expected Value` — Projected ROI, churn reduction, and strategic alignment.
2. **Pre-Persistence Schema Validator**: The proposal engine parses the generated text before saving. If any of the 7 required sections are missing or malformed, the validator rejects the output and triggers a corrective regeneration pass.
3. **Evidence Linkage**: The engine programmatically injects verified `EvidenceQuote` records directly into Section 3, ensuring every claim is backed by timestamps, source URLs, and verbatim quotes.

### Key Takeaway
Executive business documents cannot be left to freeform LLM generation. Enforce strict structural templates with code-level schema validation to guarantee consistency and completeness.

---

## 9. The Long-Running Agent Scan Pipeline vs. HTTP Request Lifecycles

### The Problem
When users clicked "Run Scan" on a competitor source, the frontend would frequently hang for 30 seconds and then throw a connection timeout or network error, leaving the user unsure whether the scan succeeded or failed.

### Why It Happened (Under the Hood)
A full competitor intelligence scan is a heavy, multi-stage pipeline:
1. Outbound network request to fetch the competitor's HTML or RSS feed.
2. DOM parsing, boilerplate suppression, and SHA-256 fingerprinting.
3. Myers diff computation against the historical snapshot.
4. Heuristic meaningfulness classification.
5. Invoking the 3-stage LangGraph AI pipeline (Researcher $\rightarrow$ Analyzer $\rightarrow$ Critic) with iterative verification loops.

Executing this entire sequence synchronously inside a single HTTP request handler takes 15–35 seconds. Web browsers, API gateways, and reverse proxies typically enforce client connection timeouts (often 10–15 seconds), terminating the TCP connection long before the backend finishes processing.

### How We Solved It
We decoupled scan execution using an **Asynchronous Job / State Pattern**:
1. **Immediate Job Acknowledgment**: When `POST /workspaces/{id}/scan` is invoked, the endpoint creates a `ScanRun` record in the database with status `PENDING`, dispatches a background task (`BackgroundTasks` in FastAPI), and immediately returns a `202 Accepted` response with the `scan_run_id` in under 100ms.
2. **Background Execution**: The background worker executes the ingestion, diffing, and LangGraph agent pipeline independently of the client HTTP connection.
3. **Granular State Transitions**: As the pipeline advances, it updates the `ScanRun` status:
   $$\text{PENDING} \longrightarrow \text{IN_PROGRESS} \longrightarrow \text{COMPLETED} \quad (\text{or } \text{FAILED})$$
4. **Client Polling**: The frontend receives the job ID instantly and polls `GET /scans/{id}` to display a real-time progress indicator, updating the dashboard smoothly once the scan completes.

### Key Takeaway
Never execute multi-stage agent workflows synchronously within a client HTTP request loop. Acknowledge the job immediately with a tracking ID and execute the agent pipeline as a decoupled background task.

---

## Summary of Engineering Architecture

| Layer | Core Problem Solved | Engineering Solution |
|---|---|---|
| **Ingestion** | Dynamic DOM noise & false alarms | Boilerplate strip-down + Heuristic Diff Classifier |
| **Ingestion** | Broken punctuation in RSS feeds | Post-sanitization regex binding (`re.sub`) |
| **Agent AI** | Hallucinations & fabricated claims | LangGraph Critic node with exact character offset mapping |
| **Agent AI** | Unstable multi-agent retry loops | StateGraph typed memory with critique feedback injection |
| **Data Layer** | Async vs. Sync database deadlocks | Harmonized synchronous execution in caller transaction |
| **Security** | Cross-tenant data leaks (IDOR) | Mandatory relational hierarchy traversal guards |
| **Testing** | Flaky, expensive CI test suites | Deterministic `MockLLM` provider running 210 tests offline |
| **Proposals** | Inconsistent, unformatted output | 7-Section schema validation engine with evidence citations |
| **API Runtime** | Request connection timeouts | 202 Accepted background worker pattern with state polling |
