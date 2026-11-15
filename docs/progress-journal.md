# TradeCraft — Core Technical Problems Faced & Engineering Solutions

A clean, plain-English breakdown of the core algorithmic, architectural, and data problems faced while building **TradeCraft**, why each occurred, and how we solved it.

---

## Quick Navigation
1. [Preventing AI Hallucinations: Exact Evidence Grounding (EGA)](#1-preventing-ai-hallucinations-exact-evidence-grounding-ega)
2. [The "Noise Avalanche": Distinguishing Real Business Changes from Web Fluff](#2-the-noise-avalanche-distinguishing-real-business-changes-from-web-fluff)
3. [Infinite Loops in Multi-Agent AI Pipelines](#3-infinite-loops-in-multi-agent-ai-pipelines)
4. [The Async vs. Sync Conflict: Preventing Database Deadlocks](#4-the-async-vs-sync-conflict-preventing-database-deadlocks)
5. [The Floating Punctuation Bug: Why Tiny Spaces Broke Verification](#5-the-floating-punctuation-bug-why-tiny-spaces-broke-verification)
6. [Data Leaks in Multi-Tenant Workspaces: Enforcing Ownership Boundaries](#6-data-leaks-in-multi-tenant-workspaces-enforcing-ownership-boundaries)
7. [The Long-Running AI Scan Problem: Preventing Frontend Timeouts](#7-the-long-running-ai-scan-problem-preventing-frontend-timeouts)
8. [Unstructured AI Proposals: Enforcing a Strict 7-Section Executive Template](#8-unstructured-ai-proposals-enforcing-a-strict-7-section-executive-template)

---

## 1. Preventing AI Hallucinations: Exact Evidence Grounding (EGA)

### What Went Wrong
When asked to summarize competitor updates, the AI frequently rephrased statements or invented plausible-sounding details (like altered pricing tiers or nonexistent features) that never actually appeared on the competitor's website. In competitive intelligence, basing a business strategy on a misquoted claim can lead to disastrous decisions.

### Why It Happened
Large language models are probabilistic text predictors. They are trained to generate smooth, persuasive text, not to be 100% literally accurate. When reading a long webpage, the AI naturally paraphrases (e.g., turning *"Plans start at \$49/mo billed annually"* into *"They dropped their base plan to forty-nine dollars"*). Because the text is rephrased, computer algorithms cannot verify if the competitor actually said that or if the AI made it up.

### How We Fixed It
We built a multi-agent verification pipeline in **LangGraph** with a strict code-level guardrail:
1. **Verbatim Quote Rule**: The researcher agent is forced to extract exact, word-for-word candidate quotes directly from the raw snapshot.
2. **The Critic Agent**: Before any insight is saved, a dedicated "Critic" agent runs a deterministic substring search through the raw stored webpage text.
3. **Character Offset Mapping**: If the quote is genuine, the system records its exact start and end character positions (`char_offset_start` to `char_offset_end`) in the source file.
4. **Evidence Grounding Accuracy (EGA)**:
   $$\text{EGA} = \left(\frac{\text{Verified Quotes}}{\text{Total Candidate Quotes}}\right) \times 100\%$$
   If $\text{EGA} < 85\%$, the finding is automatically downgraded or rejected.
5. **Proposal Firewall**: The proposal generator strictly blocks any finding that does not hold a `VERIFIED` status, ensuring proposals cite only offset-mapped evidence.

> **Key Takeaway**: Never trust an AI to verify its own facts. Pair generative models with deterministic, code-level validators that prove exact character locations in the source document.

---

## 2. The "Noise Avalanche": Distinguishing Real Business Changes from Web Fluff

### What Went Wrong
During initial tests, our automated scraper flooded the database with dozens of "Competitor Changes" every single hour, even when the competitor had not made any real business, pricing, or product updates.

### Why It Happened
Modern websites change constantly in the background even when the visible content stays identical:
- Rotating advertisement banners and tracking pixels reload.
- CSRF security tokens and session IDs refresh on every page visit.
- Timestamps tick forward (*"Updated 2 mins ago"* $\rightarrow$ *"Updated 3 mins ago"*).
- Footer copyright years bump from `© 2025` to `© 2026`.

If you naively compare raw web code, every single visit looks like a major competitor change, wasting database storage and burning expensive AI API calls.

### How We Fixed It
We built a two-stage noise reduction pipeline:
1. **DOM Sanitization**: Before saving or comparing a page, we strip out all non-content tags (`<script>`, `<style>`, `<nav>`, `<footer>`, cookie banners) and collapse all whitespace into single spaces.
2. **Heuristic Rules Engine**: We run the clean text through the **Myers unified diff algorithm** and analyze the diff chunks with a custom classifier:
   - It scans for commercial signal words: currency symbols (`$`, `€`), plan tiers (`Enterprise`, `Pro`), and action verbs (`deprecated`, `introduced`, `discontinued`).
   - If a diff only contains cosmetic updates or date changes, it is tagged as `NOISE` and immediately dropped.
   - Meaningful changes are automatically categorized into `PRICING_CHANGE`, `FEATURE_RELEASE`, `POSITIONING`, or `DEPRECATION`.

> **Key Takeaway**: Change detection is fundamentally a noise-filtering problem. You must strip layout fluff and apply deterministic rules before calling expensive AI models.

---

## 3. Infinite Loops in Multi-Agent AI Pipelines

### What Went Wrong
When our Critic agent rejected an insight because an extracted quote couldn't be verified, the multi-agent pipeline would either crash, produce a blank report, or get stuck in an infinite loop trying to re-analyze the exact same broken text over and over.

### Why It Happened
In multi-agent systems, agents pass data in a chain:
$$\text{Researcher} \longrightarrow \text{Analyzer} \longrightarrow \text{Critic}$$
If the Critic rejects a quote, simply routing the task backward causes the upstream agent to generate the exact same hallucinated quote again, because it was never told *what* was wrong. Without an exit limit, the agents will argue back and forth endlessly.

### How We Solved It
We modeled the workflow as a **LangGraph StateGraph** with structured memory and bounded retry logic:
1. **Shared State Dictionary**: Created a typed state object that flows between agents, tracking raw text, candidate quotes, critique notes, and an explicit `retry_count`.
2. **Actionable Feedback**: When the Critic rejects a quote, it attaches feedback directly into the state (e.g. *"Quote X was not found in lines 10–25; re-extract from lines 40–55"*).
3. **Bounded Routing**:
   - If $\text{EGA} \ge 85\%$, proceed to save the finding.
   - If $\text{EGA} < 85\%$ and `retry_count < 2`, loop back to the Analyzer with the Critic's notes.
   - If `retry_count >= 2`, stop immediately, mark the finding as `REJECTED`, and terminate cleanly.

> **Key Takeaway**: Autonomous AI loops must have explicit retry limits and structured feedback channels. Without exit conditions, multi-agent loops easily degrade into infinite cycles.

---

## 4. The Async vs. Sync Conflict: Preventing Database Deadlocks

### What Went Wrong
When connecting the LangGraph AI pipeline to TradeCraft's backend, background scans and automated test suites began freezing. Tests failed with:
```text
RuntimeError: Task got Future attached to a different loop
OperationalError: database is locked
```

### Why It Happened
LangGraph and modern AI libraries are written using asynchronous Python (`async`/`await`). However, TradeCraft's web routers, user authentication, and 200+ unit test fixtures were built using synchronous SQLAlchemy sessions (`sync`). 

When synchronous test threads tried to trigger an asynchronous AI graph, competing event loops were spawned. Because databases (especially SQLite during automated testing) lock files during active transactions, having an async coroutine query the database while the parent synchronous thread held an open session caused an immediate deadlock.

### How We Solved It
Instead of rewriting 200+ working tests to be async, we adapted the AI boundary to match our application:
1. Wrapped the LangGraph pipeline execution so graph nodes run within the caller's synchronous database transaction.
2. Passed the active database `Session` directly into the agent state.
3. Engineered the database writes so the snapshot, diff, finding, and evidence quotes all commit together in one **single, atomic ACID transaction**.
4. If any step fails, the entire transaction rolls back cleanly, preventing orphaned records.

> **Key Takeaway**: When introducing new AI tools into an existing application, adapt the AI wrapper to fit your architecture—never rewrite working database logic just to satisfy an external library.

---

## 5. The Floating Punctuation Bug: Why Tiny Spaces Broke Verification

### What Went Wrong
Legitimate competitor quotes extracted from RSS feeds were failing exact verification in the Critic agent, even though the text was clearly visible on the competitor's webpage.

### Why It Happened
Competitor blog feeds frequently put links around the last word of a sentence:
```html
<p>Patched critical security <a href="/advisory">vulnerability</a>.</p>
```
When our HTML cleaner stripped the link tags, it inserted a space to keep words from colliding. But because the period was located right after the closing `</a>` tag, the cleaner accidentally inserted a space between the word and the period:
```text
"Patched critical security vulnerability ."
```
While human eyes overlook a floating space before a period, our Critic agent performs strict character-by-character substring matching. Because the candidate quote had `"vulnerability ."` but the raw website had `"vulnerability."`, the search failed, causing the Critic to reject genuine evidence.

### How We Solved It
We added a regex post-processing filter right after HTML tag stripping:
```python
text = re.sub(r"\s+([.,!?;:])", r"\1", text)
```
This rule detects any whitespace sitting directly in front of punctuation marks and binds the punctuation snug against the word. This restored natural grammar and enabled 100% exact verbatim character matching in the Critic agent.

> **Key Takeaway**: Data cleaning for AI verification requires typographic precision. A single misplaced space around punctuation will break exact substring verification.

---

## 6. Data Leaks in Multi-Tenant Workspaces: Enforcing Ownership Boundaries

### What Went Wrong
In early API versions, if an authenticated user from Company A guessed the ID number of a competitor or report belonging to Company B, the backend might accidentally return it.

### Why It Happened
Verifying *who* a user is (Authentication via JWT) does not automatically verify *what* they are allowed to see (Authorization). Querying directly by entity ID (`SELECT * FROM competitors WHERE id = 5`) ignores tenant ownership boundaries, creating an Insecure Direct Object Reference (IDOR) vulnerability.

### How We Solved It
We enforced **Relational Ownership Guards** across all database queries:
1. Every entity in TradeCraft belongs to a strict hierarchy:
   $$\text{User} \longrightarrow \text{Workspace} \longrightarrow \text{Competitor} \longrightarrow \text{Source} \longrightarrow \text{Finding} \longrightarrow \text{Proposal}$$
2. Every database query joins through the `Workspace` table and filters by the authenticated user's active `workspace_id`:
   ```python
   competitor = db.query(Competitor).join(Workspace).filter(
       Competitor.id == competitor_id,
       Workspace.id == current_user_workspace_id
   ).first()
   ```
3. If an entity exists but belongs to another workspace, the API returns `404 Not Found` rather than `403 Forbidden`, preventing attackers from confirming whether other companies' IDs even exist.

> **Key Takeaway**: Authentication is not authorization. Every database query in a multi-tenant system must join through the tenant ownership boundary.

---

## 7. The Long-Running AI Scan Problem: Preventing Frontend Timeouts

### What Went Wrong
Clicking "Run Scan" on a competitor source caused the user's browser to freeze for 25 seconds, often ending in a `504 Gateway Timeout` or broken connection error.

### Why It Happened
A full competitive intelligence scan does a lot of work:
1. Makes network calls to fetch competitor web pages.
2. Cleans HTML, extracts feeds, and calculates cryptographic hashes.
3. Computes unified diffs and classifies changes.
4. Executes the 3-stage LangGraph AI pipeline with multiple model calls.

Doing all of this synchronously inside one HTTP request takes 15–30 seconds. Standard web browsers and cloud gateways expect quick responses (<1–2 seconds) and disconnect if a request takes too long.

### How We Solved It
We decoupled scans using an **Asynchronous Background Worker Pattern**:
1. **Instant Response**: When the user clicks "Run Scan", the server creates a `ScanRun` record with status `PENDING`, launches a background task, and responds in under 50ms with `202 Accepted` and a `scan_id`.
2. **Background Processing**: The server executes the scraping, diffing, and AI pipeline in the background without holding open the user's HTTP connection.
3. **State Transitions**: The scan updates its state in the database as it progresses:
   $$\text{PENDING} \longrightarrow \text{IN_PROGRESS} \longrightarrow \text{COMPLETED} \quad (\text{or } \text{FAILED})$$
4. **Client Polling**: The frontend displays an instant loading spinner and polls `GET /scans/{id}` until the scan completes, updating the UI smoothly.

> **Key Takeaway**: Never run heavy AI workflows inside blocking HTTP request handlers. Accept the task immediately, run it in the background, and report progress asynchronously.

---

## 8. Unstructured AI Proposals: Enforcing a Strict 7-Section Executive Template

### What Went Wrong
When asked to write strategic counter-proposals based on verified competitor moves, the AI produced rambling, unstructured essays. It would write three paragraphs about the problem, completely forget to propose a feature response, or omit the pricing strategy.

### Why It Happened
Without strict guardrails, language models treat document generation as open-ended conversation. They prioritize whatever topic seems most prominent in the prompt, producing inconsistent documents that company leaders cannot easily compare or evaluate.

### How We Solved It
We built a dedicated **Proposal Engine** with code-level schema validation:
1. **The 7-Section Standard**: Every generated proposal must contain exactly seven Markdown H2 sections:
   - `## 1. Problem / Opportunity` — Commercial urgency and market shift.
   - `## 2. Competitor Change` — Verified competitor adjustments.
   - `## 3. Evidence` — Verbatim snapshot quotes with exact source links.
   - `## 4. Strategic Impact` — Impact on retention, sales, and positioning.
   - `## 5. Proposed Response` — Recommended strategic countermeasure.
   - `## 6. Suggested Features/Work` — Phased engineering roadmap.
   - `## 7. Expected Value` — Projected ROI and churn reduction.
2. **Pre-Save Validator**: The backend inspects the generated Markdown before saving. If any of the 7 sections are missing or out of order, the output is rejected and regenerated.
3. **Automated Evidence Linkage**: Section 3 is programmatically populated with verified evidence quotes directly from the database, ensuring every claim is backed by timestamps and URLs.

> **Key Takeaway**: Executive documents cannot be left to freeform AI prompts. Enforce strict templates with code-level schema validation to guarantee structured, predictable output.

---

## Summary of Core Architectural Solutions

| Challenge | Root Cause | Engineering Fix |
|---|---|---|
| **AI Hallucinations** | Probabilistic token prediction | LangGraph Critic node with exact character-offset verification |
| **Scraping Noise** | Ephemeral DOM shifts (ads, tokens, dates) | DOM sanitization + Heuristic Meaningfulness Classifier |
| **Agent Infinite Loops** | Feedbackless rejection loops | StateGraph typed memory with bounded retry limits |
| **Database Deadlocks** | Async AI loop vs. Sync SQLAlchemy | Unified synchronous execution within caller's atomic transaction |
| **Punctuation Artifacts** | Tag stripping separating punctuation | Post-sanitization regex binding (`re.sub`) |
| **Cross-Tenant Leaks** | Querying purely by entity ID (IDOR) | Mandatory `Workspace` relational traversal on every query |
| **Request Timeouts** | Heavy 25s scans blocking HTTP handlers | 202 Accepted background worker pattern with status polling |
| **Unstructured Output** | Unconstrained LLM text generation | 7-Section Markdown schema validator with programmatically injected evidence |
