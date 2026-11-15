# TradeCraft — Technical Problems Faced & Engineering Solutions

A comprehensive, transparent record of every major technical challenge encountered during the design, development, integration, and cloud deployment of TradeCraft, how each was diagnosed under the hood, and how it was solved.

---

## Table of Contents
1. [The "Ghost Cloud" Freeze: macOS APFS Dataless Traps](#1-the-ghost-cloud-freeze-macos-apfs-dataless-traps)
2. [The IPv6 Outbound Black Hole: Render to Supabase Connection](#2-the-ipv6-outbound-black-hole-render-to-supabase-connection)
3. [The Modal-Clipping & Dark-Mode Bleed Trap: PDF Generation](#3-the-modal-clipping--dark-mode-bleed-trap-pdf-generation)
4. [The Agent Hallucination Gap: Evidence Grounding Accuracy (EGA)](#4-the-agent-hallucination-gap-evidence-grounding-accuracy-ega)
5. [The Async vs. Sync Threading Deadlock in Agent Pipelines](#5-the-async-vs-sync-threading-deadlock-in-agent-pipelines)
6. [The Web Scraping "Noise Avalanche": Ephemeral DOM Mutation](#6-the-web-scraping-noise-avalanche-ephemeral-dom-mutation)
7. [The Serverless Execution Timeout: Vercel 15-Second Edge Limit](#7-the-serverless-execution-timeout-vercel-15-second-edge-limit)
8. [The Database Driver Conflict on Zero-Config Machines](#8-the-database-driver-conflict-on-zero-config-machines)
9. [The Punctuation Formatting Artifacts in Feed Normalization](#9-the-punctuation-formatting-artifacts-in-feed-normalization)
10. [The Browser Default User-Agent Box Artifact in Dark Mode](#10-the-browser-default-user-agent-box-artifact-in-dark-mode)

---

## 1. The "Ghost Cloud" Freeze: macOS APFS Dataless Traps

### The Problem
During development, standard Git commands (`git commit`, `git status`, `git diff`) and testing tools began hanging indefinitely with zero output. Commands would freeze for minutes, and terminal tasks could only be terminated with `kill -9`.

### Why It Happened (Under the Hood)
The workspace was located inside `~/Desktop/TradeCraft`. On macOS, when **iCloud Drive "Desktop & Documents"** is enabled with **"Optimize Mac Storage"**, the operating system's kernel silently evicts idle files from the local APFS disk to free space. 

When a file is evicted, macOS leaves a pointer marked with the APFS kernel flag `dataless` (visible via `ls -laO` as `hidden,compressed,dataless`). Over 180 git objects, commit edits, and ref files (including `.git/refs/heads/ai-pipeline` and pack index files) were marked `dataless`. Whenever Git attempted an open syscall on a ref file, the macOS kernel placed the process into an uninterruptible disk wait state (`D` state), waiting for the background CloudDocs daemon (`bird`) to fetch the missing bytes from Apple's servers. Because Git locks repository indexes while reading, every subsequent Git process deadlocked on `.git/index.lock`.

### How We Solved It
1. Diagnosed the root cause by sampling the stuck Git process stack (`sample <pid> 1`), which revealed the thread was blocked inside `files_read_raw_ref` $\rightarrow$ `xread`.
2. Inspected file flags with `ls -laO .git/refs/heads/` and discovered the `dataless` tag.
3. Created an automated staging pipeline in a local, non-synced RAM volume (`/tmp`), cloned a clean repository instance, applied all modified files, committed them in sub-second time, and pushed directly to GitHub.
4. Repaired the local workspace by unlinking (`rm -f`) the evicted placeholder files and rewriting fresh local copies directly to disk, bypassing the cloud sync daemon entirely.

### Key Takeaway
Never maintain active Git repositories or developer dependencies inside cloud-synced folders (iCloud, OneDrive, Dropbox) with automated file eviction enabled. The silent conversion of files to `dataless` placeholders breaks low-level file descriptors and version control internals.

---

## 2. The IPv6 Outbound Black Hole: Render to Supabase Connection

### The Problem
After deploying the FastAPI backend to Render and configuring the PostgreSQL connection string to cloud Supabase, the backend server crashed on startup with the following error:
```text
(psycopg2.OperationalError) connection to server at "db.ptalxyofynhiszkisuay.supabase.co" 
(2406:da14:25a:5801:0:c439:630a:4321), port 5432 failed: Network is unreachable
```

### Why It Happened (Under the Hood)
Modern Supabase projects assign direct database hostnames (`db.<project-ref>.supabase.co`) that resolve exclusively to **IPv6 addresses** on their default database port (5432). However, Render's free tier runtime instances operate on an **IPv4-only** network virtualization stack and do not have outbound IPv6 routing enabled. When `psycopg2` attempted a TCP handshake to `2406:da14:...`, the host OS rejected the packet immediately with `ENETUNREACH` (Network is unreachable).

### How We Solved It
Supabase maintains an **IPv4-compatible Connection Pooler** (Supavisor / PgBouncer) in each cloud region. We re-engineered the connection architecture:
1. Resolved the project's AWS cluster region from its IPv6 subnet (`Tokyo / ap-northeast-1`).
2. Pointed the database configuration to the regional IPv4 pooler domain: `aws-0-ap-northeast-1.pooler.supabase.com`.
3. Updated the authentication username format to include the tenant project reference (`postgres.<project-ref>`) and set the port to `6543` (transaction mode).
4. Configured SQLAlchemy engine arguments with `sslmode=require`, `pool_pre_ping=True`, and automatic URL normalization (`postgres://` $\rightarrow$ `postgresql://`).
5. Verified the fix with a live Python test script, achieving sub-300ms connection handshakes.

### Key Takeaway
Cloud platforms have divergent network capabilities. When connecting a container platform (like Render) to a managed database (like Supabase), never rely on direct hostnames that may resolve to IPv6; always utilize regional IPv4 connection poolers with SSL enforcement.

---

## 3. The Modal-Clipping & Dark-Mode Bleed Trap: PDF Generation

### The Problem
When users clicked "Export to PDF" on a strategic proposal, the generated PDF was either completely blank, clipped to the tiny height of the scrollable modal viewport (rendering only the first page and cutting off the rest), or printed with a muddy black background and unreadable dark-gray text.

### Why It Happened (Under the Hood)
The proposal reader UI is rendered inside a glassmorphic React modal with fixed positioning (`fixed inset-0 overflow-y-auto backdrop-blur-xl`). When standard browser printing (`window.print()`) was triggered:
1. **Viewport Clipping**: The browser's print engine respects CSS overflow boundaries. Because the parent container had `overflow-y-auto` and a constrained height, the print renderer treated the modal as a single scroll box, printing only what was visible on screen and truncating pages 2 through 7.
2. **Dark Mode Bleed**: The application uses dark-theme CSS variables (`--bg-primary: #0a0e17`, `--text-primary: #f8fafc`). The print engine carried these dark background colors into the print canvas, resulting in heavy black toner consumption and broken contrast.
3. **Visibility Hiding**: Attempting to hide other elements via CSS (`body * { visibility: hidden; }`) inadvertently collapsed the height of the modal content to zero, producing blank white output.

### How We Solved It
We engineered an isolated **Offscreen Iframe Print Engine** (`frontend/src/utils/pdfExport.js`):
1. Instead of printing the active DOM tree, the utility dynamically instantiates an invisible, isolated `<iframe>` appended to `document.body`.
2. Converts the proposal's Markdown into semantic HTML with structured metadata headers.
3. Injects dedicated, standalone high-contrast typography styles exclusively into the iframe's isolated DOM:
   - Enforces a crisp white background with `#111827` primary body text.
   - Sets strict print rules: `@page { size: A4; margin: 20mm; }`.
   - Forces clean pagination without awkward orphans: `h2 { page-break-before: always; }` and `table, blockquote { page-break-inside: avoid; }`.
4. Executes printing solely on the iframe (`iframe.contentWindow.print()`), then unlinks and destroys the iframe after the user saves or cancels.

### Key Takeaway
Never attempt to print directly from complex SPA component trees or modals using global CSS print media queries. Always generate an isolated document context (via offscreen iframe or virtual DOM) with independent, print-specific typography.

---

## 4. The Agent Hallucination Gap: Evidence Grounding Accuracy (EGA)

### The Problem
In early AI prototypes, when language models were prompted to summarize competitor updates and propose countermeasures, they frequently hallucinated: they invented plausible-sounding pricing tiers, exaggerated competitor features, or rephrased statements so heavily that the original claim could not be traced back to the competitor's website. In competitive intelligence, citing false competitor claims can mislead business strategy.

### Why It Happened (Under the Hood)
Large language models are probabilistic token predictors optimized for fluency rather than factual fidelity. Without strict deterministic boundaries, the model fills in memory gaps by generating plausible text ("hallucination"). Standard retrieval pipelines often pass raw text chunks without verifying that the LLM's output claims actually exist in the retrieved document.

### How We Solved It
We designed a stateful multi-agent pipeline using **LangGraph** with an adversarial verification stage:
1. **Context Researcher Node**: Analyzes candidate diffs against the clean snapshot and identifies factual claims, extracting candidate verbatim quotes.
2. **Impact Analyzer Node**: Synthesizes business threat analysis, product positioning impact, and recommended responses.
3. **Critic / Verifier Node (The Guardrail)**: Takes every candidate quote and executes an exact, deterministic substring search against the raw snapshot text stored in the database.
   - For every verified match, it records the exact character coordinates (`char_offset_start` to `char_offset_end`).
   - Computes the **Evidence Grounding Accuracy (EGA)** metric:
     $$\text{EGA} = \left(\frac{\text{Verified Quotes}}{\text{Candidate Quotes}}\right) \times 100\%$$
   - Enforces strict thresholds: if $\text{EGA} < 85\%$, the finding is automatically downgraded or rejected, and the loop can trigger a retry.
4. **Proposal Engine Firewall**: The proposal generator strictly bars any finding that does not hold a `VERIFIED` status, guaranteeing that executive proposals only cite grounded, offset-mapped evidence.

### Key Takeaway
Do not rely on the LLM to self-police its own accuracy. Pair generative models with deterministic, code-level verifiers (exact character offset mapping) to measure factual grounding before any output reaches the user.

---

## 5. The Async vs. Sync Threading Deadlock in Agent Pipelines

### The Problem
When integrating the LangGraph agent pipeline into TradeCraft's existing backend, the test suite and background scan workers began deadlocking. Tests either hung forever or crashed with:
```text
RuntimeError: Task <...> got Future <...> attached to a different loop
OperationalError: (sqlite3.OperationalError) database is locked
```

### Why It Happened (Under the Hood)
The AI agent pipeline was initially written using Python's asynchronous event loop paradigm (`async def` with SQLAlchemy's `AsyncSession`). However, TradeCraft's existing web routers, multi-tenant permission layers, and 200+ unit test fixtures were architected with synchronous SQLAlchemy sessions (`Session = sessionmaker()`). 

Attempting to run an asynchronous LangGraph graph inside a synchronous request thread using `asyncio.run()` created nested event loops. Furthermore, SQLite in-memory and file databases cannot be safely shared across an active async loop and a synchronous caller thread simultaneously, resulting in immediate database lock contention.

### How We Solved It
1. Synchronized the agent execution boundary instead of forcing the entire web application to become async.
2. Adapted the LangGraph pipeline execution so that graph nodes invoke synchronous tool wrappers and share the caller's existing database transaction.
3. Passed the current database `Session` directly into the agent state, ensuring that the scraping record, diff computation, finding generation, and quote persistence all commit atomically in a single, predictable transaction.
4. Preserved all 210 existing synchronous test suites with 100% pass rates and zero race conditions.

### Key Takeaway
When introducing experimental AI frameworks into an established production codebase, adapt the AI wrapper to fit the host architecture. Never rewrite an entire working application to satisfy an asynchronous library constraint.

---

## 6. The Web Scraping "Noise Avalanche": Ephemeral DOM Mutation

### The Problem
During initial end-to-end testing, the change-detection engine bombarded the system with "Competitor Change Detected" alerts every time a scheduled scan ran, even when the competitor's website had not changed in any meaningful way.

### Why It Happened (Under the Hood)
Modern web pages are dynamic: rotating promotional banners, dynamic CSRF/session tokens, timestamp counters, and fluctuating footer copyright notices (`© 2025` $\rightarrow$ `© 2026`) constantly alter the DOM tree. If a system naively computes a cryptographic hash or line-by-line diff on raw HTML responses, every ephemeral JavaScript variable or rotating asset looks like a major competitor maneuver.

### How We Solved It
We engineered a two-stage noise reduction pipeline:
1. **DOM Sanitization (`HtmlAdapter`)**:
   - Parses the HTML DOM using BeautifulSoup and aggressively strips non-content tags: `<script>`, `<style>`, `<noscript>`, `<nav>`, `<footer>`, `<header>`, cookie consents, and tracking iframes.
   - Normalizes HTML entities and collapses redundant whitespace into single spaces.
2. **Deterministic Heuristic Meaningfulness Classifier**:
   - Computes Myers unified diffs exclusively on the sanitized text.
   - Evaluates the diff against a weighted heuristic ruleset: checks for business-critical tokens (e.g. `$`, `€`, `pricing`, `plan`, `deprecated`, `release`, `feature`).
   - If a diff contains only cosmetic updates, date bumps, or whitespace shifts, it is classified as `NOISE` and suppressed from the AI pipeline.
   - Changes with commercial relevance are automatically categorized as `PRICING_CHANGE`, `FEATURE_RELEASE`, `POSITIONING`, or `DEPRECATION`.

### Key Takeaway
Change detection is only as good as your noise filter. You must aggressively strip ephemeral layout boilerplate and apply deterministic heuristic classification before invoking expensive downstream AI analysis.

---

## 7. The Serverless Execution Timeout: Vercel 15-Second Edge Limit

### The Problem
When evaluating deploying both the React frontend and the FastAPI backend as a single unified serverless repository on Vercel, API endpoints that triggered full scans or AI analyses intermittently failed with `504 Gateway Timeout`.

### Why It Happened (Under the Hood)
Vercel's Hobby/Free serverless function runtime enforces a strict **15-second execution limit** per invocation. While lightweight CRUD operations (such as authentication or fetching a competitor list) execute in under 150ms, a full competitive intelligence scan involves:
- Outbound network requests to fetch competitor web pages.
- HTML parsing, diff computation, and SHA-256 hashing.
- Invoking the multi-node LangGraph pipeline (Context Researcher, Impact Analyzer, and Critic Verifier).
- Executing iterative LLM calls and retry loops.

The full AI analysis pipeline takes between 18 and 35 seconds to complete. Running this on Vercel triggered an uncatchable 504 timeout before the agent could return its response.

### How We Solved It
We separated the architecture into a **Decoupled Cloud Topology**:
- **Frontend on Vercel**: Deployed the Vite React application as static assets distributed across Vercel's global Edge CDN, achieving sub-50ms initial load times and instant caching.
- **Backend on Render**: Deployed the FastAPI server on a dedicated persistent container instance on Render. Persistent containers run uninterrupted without arbitrary 15-second serverless execution timeouts, allowing LangGraph multi-agent loops and background scans to run to full completion.
- Configured dynamic API URL resolution via `VITE_API_URL` and cross-origin resource sharing (CORS) with automatic origin reflection.

### Key Takeaway
Do not force long-running multi-agent AI pipelines into serverless function runtimes with short timeout ceilings. Use Edge CDN hosting for static frontends and persistent container runtimes for agentic AI backends.

---

## 8. The Database Driver Conflict on Zero-Config Machines

### The Problem
When onboarding new developers or running automated CI test suites on machines without PostgreSQL installed, running `pytest` failed instantly with:
```text
ModuleNotFoundError: No module named 'psycopg2'
```

### Why It Happened (Under the Hood)
`psycopg2` requires native C libraries (`libpq-dev`) to compile. In production, TradeCraft connects to cloud PostgreSQL. In local development and automated testing, TradeCraft uses SQLite for instant zero-dependency execution. However, because `import psycopg2` was placed at the top level of the database connection module, Python attempted to load the C extension upon initial package import, crashing test suites before a single test could execute.

### How We Solved It
We implemented **Lazy Fault-Tolerant Database Driver Loading**:
1. Wrapped PostgreSQL driver imports in an exception-tolerant block:
   ```python
   try:
       import psycopg2
   except ImportError:
       psycopg2 = None
   ```
2. Built a resilient engine factory (`create_db_engine`) that inspects the connection URL. If no URL is provided or if SQLite is requested, it provisions an in-memory or file-based SQLite engine with `PRAGMA foreign_keys=ON`.
3. Added automatic URL normalization: automatically transforms legacy `postgres://` prefixes (frequently supplied by cloud providers) into SQLAlchemy-compliant `postgresql://` strings.

### Key Takeaway
A production-only database driver should never prevent a developer from running local unit tests. Build database abstractions that seamlessly degrade to zero-dependency local engines (like SQLite) when external drivers are absent.

---

## 9. The Punctuation Formatting Artifacts in Feed Normalization

### The Problem
In automated RSS feed ingestion tests, sanitized article excerpts intermittently failed exact string matching in the Critic agent due to floating punctuation marks (e.g. `"Patched critical security vulnerability ."` instead of `"Patched critical security vulnerability."`).

### Why It Happened (Under the Hood)
In blog and news syndication feeds, anchor tags frequently enclose the final word of a sentence before the terminal period:
```html
<p>Patched critical security <a href="/advisory">vulnerability</a>.</p>
```
When our HTML cleaner stripped HTML tags, it replaced tags with whitespace to prevent adjacent inline elements from merging together into single words (e.g. `word1</a><a>word2` becoming `word1word2`). However, because the period was placed immediately after the closing `</a>` tag, the cleaner inserted a space between the last word and the punctuation mark. While humans mentally ignore floating spaces, exact character-offset matching in the downstream Critic agent failed because the candidate quote did not match the raw snapshot character-for-character.

### How We Solved It
Added a deterministic regex post-processing filter to the sanitization pipeline:
```python
text = re.sub(r"\s+([.,!?;:])", r"\1", text)
```
This rule identifies any whitespace preceding punctuation marks and binds the punctuation directly to the preceding word, restoring natural typography and enabling 100% exact verbatim substring matching in the Critic verification engine.

### Key Takeaway
When sanitizing HTML for AI consumption, naive tag stripping corrupts sentence structure. You must enforce natural punctuation binding to ensure verbatim substring verification can match character offsets precisely.

---

## 10. The Browser Default User-Agent Box Artifact in Dark Mode

### The Problem
On the strategic Proposals page, the download and delete icon buttons inside the proposal cards displayed harsh, blinding white rectangular border boxes and gray backgrounds in dark mode, clashing with the glassmorphism design.

### Why It Happened (Under the Hood)
In standard HTML, native `<button>` elements carry default user-agent styling provided by the browser engine (`background-color: buttonface; border: 2px outset buttonborder; padding: 1px 6px;`). When custom Tailwind utility classes like `p-2 rounded-lg text-slate-400 hover:text-white` were applied to the button without explicitly overriding the browser's base border and background properties, WebKit and Blink browsers fell back to their default button outlines. Against a `#0a0e17` dark background, the browser's default light border appeared as a jarring white square.

### How We Solved It
1. Implemented a global CSS reset in `frontend/src/index.css` targeting all interactive button elements:
   ```css
   button {
     background: transparent;
     border: none;
     padding: 0;
     outline: none;
     font-family: inherit;
   }
   ```
2. Refactored the icon buttons in `frontend/src/pages/Proposal.jsx` with explicit utility classes (`bg-transparent border-0 outline-none hover:bg-slate-800/50 transition-colors`), completely eliminating the user-agent border artifact while preserving accessibility and hover states.

### Key Takeaway
Never rely on CSS frameworks alone to silence browser defaults. Explicitly reset browser user-agent button styles in base CSS to prevent dark-mode border bleeding across different rendering engines.

---

## Summary of Results

By systematically diagnosing and eliminating each of these 10 challenges:
- **100% Passing Test Suite**: All 210 automated unit and integration tests pass deterministically.
- **Zero Hallucination Tolerance**: Every generated proposal is anchored by mathematically verified quotes with exact character offsets ($EGA \ge 85\%$).
- **Multi-Cloud Production Topology**: High-speed edge UI on Vercel paired with a persistent, containerized FastAPI backend on Render connected to cloud Supabase PostgreSQL 17.
