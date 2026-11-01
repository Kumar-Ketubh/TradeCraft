# TradeCraft — Engineering Journey & Progress Journal

> **AI-Powered Competitive Intelligence & Executive Proposal Engine**  
> *A transparent record of how TradeCraft was built, the real problems we encountered, how we solved them, and the engineering principles behind every decision.*

---

## 🧭 Project Overview: Why TradeCraft?

When competing in modern software markets, companies change fast: they quietly raise prices, sneak in feature deprecations, launch new capabilities, and alter their marketing positioning. 

Most existing change-monitoring tools only notify you that *"page X was updated."* They leave teams drowning in noise (like copyright year bumps or cookie banner updates) and don't answer the questions leaders actually care about:
1. **What changed?** (Precise diffs, not page dumps)
2. **Why does it matter?** (Business and commercial implications)
3. **What evidence proves it?** (Verbatim quotes from the actual page, not AI hallucinations)
4. **What should we do about it?** (Concrete countermeasures and feature roadmaps)

TradeCraft was designed from the ground up to solve this complete loop in one unified, automated system.

---

## 🏗️ The 5 Development Phases: What We Built

Rather than dumping repetitive code listings, here is how TradeCraft evolved step-by-step:

```text
Phase 1: Foundation ──> Phase 2: Management ──> Phase 3: Ingestion ──> Phase 4: Diffing & Noise ──> Phase 5: AI & Proposals
(React + FastAPI)      (Auth & Workspaces)     (Scrapers & Storage)    (Myers Diff & Filters)     (LangGraph + EGA Guard)
```

### Phase 1: Project Foundation & Architecture
- **Goal:** Set up a clean, modern full-stack scaffolding with guaranteed local dev ergonomics.
- **Frontend:** Built with React 19 and Vite 8 for instant hot-module reload, styled with a custom clean-slate theme supporting both light and dark modes.
- **Backend:** High-performance FastAPI server with structured dependency injection and automated health checks (`/health`).
- **Database:** PostgreSQL for production with seamless SQLite fallback for local development.

### Phase 2: Multi-Tenant Workspace & Core Management
- **Goal:** Enable multi-tenant user isolation so teams can securely manage their own competitor targets.
- **Data Hierarchy:** Strict relational hierarchy: `User` $\rightarrow$ `Workspace` $\rightarrow$ `Competitor` $\rightarrow$ `Source`.
- **Security:** JWT authentication with bcrypt password hashing and token expiration guards.
- **APIs:** Complete RESTful CRUD endpoints with ownership verification preventing cross-tenant data leaks.

### Phase 3: Automated Ingestion & Snapshot Engine
- **Goal:** Reliably fetch competitor websites and news feeds without getting blocked or crashing on broken pages.
- **Adapters:** Built resilient collectors for standard web pages (`HtmlAdapter`) and syndication feeds (`RssAdapter` supporting RSS 2.0 and Atom 1.0).
- **Boilerplate Suppression:** Automated strip-down of noisy HTML artifacts (`<script>`, `<style>`, navigation bars, cookie banners, tracking scripts) prior to hashing.
- **Snapshot Storage:** Cryptographic SHA-256 fingerprinting of clean content to record historical snapshots over time.

### Phase 4: Deterministic Diffing & Smart Noise Filtering
- **Goal:** Compare snapshots mathematically and filter out cosmetic changes so users only see substantive updates.
- **Myers Diff Engine:** Line-by-line unified diff calculation computing exact additions, deletions, and similarity scores.
- **Zero-Cost Heuristic Classifier:** A fast, deterministic rules engine that categorizes updates into `PRICING_CHANGE`, `FEATURE_RELEASE`, `POSITIONING`, `DEPRECATION`, or filters them as `NOISE`.

### Phase 5: Multi-Agent AI Intelligence & Executive Proposals
- **Goal:** Run an autonomous agent pipeline that verifies facts against raw snapshots and produces executive-ready project counter-proposals.
- **LangGraph StateGraph:** A coordinated multi-agent loop:
  1. **Context Researcher:** Spots candidate quotes and factual claims.
  2. **Impact Analyzer:** Evaluates threats to pipeline revenue, customer churn, and market positioning.
  3. **Critic / Verifier:** Scans verbatim text, calculates character offsets, and computes an Evidence Grounding Accuracy ($EGA$) score.
- **7-Section Counter-Proposal Generator:** Turns verified findings into an executive proposal with problem analysis, verbatim cited evidence, response strategy, phased work breakdown, and expected ROI.
- **Zero-Paid-API Mandate:** Fully operational offline via deterministic mock models, with native plug-and-play support for free-tier Groq, Gemini, or local Ollama.

---

## 🥊 Real Problems We Faced & How We Fixed Them (In Plain English)

Building a complex system rarely goes smoothly. Here are the 7 biggest technical hurdles we hit, explained in simple, everyday language without the confusing buzzwords.

---

### 1. The "App Won't Start on My Laptop" Problem (Database Drivers)

* **The Problem:** Whenever a developer tried to run the app or run tests locally, Python immediately crashed with an angry error: `ModuleNotFoundError: No module named 'psycopg2'`.
* **Why It Happened (In Plain English):** `psycopg2` is the connector library used to talk to PostgreSQL databases. In our production environment, we use PostgreSQL. But for local testing and classroom demos, we use SQLite—which is lightweight and built directly into Python. However, because our database setup script had `import psycopg2` right at the very top of the file, Python tried to load the PostgreSQL connector *even when the developer only wanted to use SQLite*. If their computer didn't have PostgreSQL installed, the whole app refused to boot.
* **How We Fixed It:** We wrapped the import in a safe check (`try...except ImportError`). If `psycopg2` is installed, the app happily connects to PostgreSQL. If it's missing, the app doesn't crash—it gracefully falls back to local SQLite mode and prints a friendly log notice.
* **The Lesson:** Never let a production-only dependency crash local development. Always provide a painless fallback for developers running the code on a clean machine.

---

### 2. The Broken Password Machine (Legacy Libraries vs. Modern Python)

* **The Problem:** New user registration was randomly breaking with cryptographic errors during password hashing.
* **Why It Happened (In Plain English):** We were originally using an older helper library called `passlib` to encrypt passwords. Modern Python (Python 3.13) and newer versions of the underlying security engine (`bcrypt 5.0`) changed how passwords are formatted. `passlib` hasn't been updated in years, so it couldn't understand the new format and choked.
* **How We Fixed It:** We cut out the middleman. We removed `passlib` and wrote direct calls to the official, actively-maintained `bcrypt` library (`bcrypt.hashpw` and `bcrypt.checkpw`).
* **The Lesson:** In security and cryptography, unmaintained "convenience" wrappers eventually become liabilities. Sticking to direct, well-supported official libraries is safer and simpler.

---

### 3. The "False Alarm" Flood (Web Scraping Noise)

* **The Problem:** The system kept bombarding the feed with "Competitor Changed!" notifications, but when we checked the website, nothing important had actually changed.
* **Why It Happened (In Plain English):** Modern websites are constantly changing invisible details: advertising banners reload, session tokens rotate, timestamps update, and copyright footers change from `2025` to `2026`. If you just compare raw website code, every tiny background change looks like a massive event.
* **How We Fixed It:** We built a two-stage filter:
  1. **HTML Sanitization:** Before saving a web page, we strip out everything that isn't core content—removing `<script>`, `<style>`, cookie popups, and footer menus.
  2. **Heuristic Filter:** We wrote a rules engine that checks *what* changed. If the only difference is a number in a copyright notice or random whitespace, it's flagged as `NOISE` and hidden. But if a dollar sign appears or product tier names shift, it's immediately marked as `MEANINGFUL`.
* **The Lesson:** More data isn't better if it's junk. Change detection is only useful if you aggressively throw away the fluff before alarming the user.

---

### 4. The "Ghost Space" in News Feeds (Punctuation Formatting Bug)

* **The Problem:** In our automated test suite, an RSS test failed with an odd discrepancy: text extracted from an article summary had a floating space right before the period (e.g., `"Patched security vulnerability ."` instead of `"Patched security vulnerability."`).
* **Why It Happened (In Plain English):** In the competitor's blog post, the last word was inside a clickable link: `<a href="...">vulnerability</a>.`. When our cleaner stripped away the HTML tags, it replaced them with a space so words wouldn't accidentally get glued together. But because the period was sitting right against the closing tag, that space was inserted right between the word and the period!
* **How We Fixed It:** We added a smart punctuation cleanup rule (`re.sub(r"\s+([.,!?;:])", r"\1", text)`). It looks for any space sitting in front of punctuation marks and pulls the punctuation snug against the word.
* **The Lesson:** Cleaning text isn't just about deleting tags; you have to respect natural grammar and punctuation rules so downstream AI models receive clean, human-readable sentences.

---

### 5. The Sync vs. Async Tug-of-War (Merging the AI Pipeline)

* **The Problem:** When we integrated the LangGraph AI pipeline into TradeCraft, our entire test suite threatened to collapse. The AI pipeline was written using asynchronous Python (`async def` with `AsyncSession`), while the rest of TradeCraft's 200+ tests and database models were built using synchronous SQLAlchemy (`Session = sessionmaker()`).
* **Why It Happened (In Plain English):** In Python, "async" and "sync" code are like two different electrical currents. If you try to run an async database query inside a normal synchronous function without care, Python can deadlock, freeze, or lock the database file entirely. Rewriting all 200+ existing tests to be async would have taken days and risked introducing dozens of subtle bugs.
* **How We Fixed It:** We harmonized the models! Instead of forcing the main app to become async, we adapted the AI pipeline to execute synchronously within TradeCraft's existing database transaction. We kept the exact same database session for both the web app and the AI agent, allowing all 206+ existing tests to pass without modifying our core architecture.
* **The Lesson:** When merging experimental AI code into an established web application, adapt the AI wrapper to fit the application's architecture—never rewrite a working application just to accommodate an experimental pipeline.

---

### 6. The "Lying AI" Problem (Hallucinations & Evidence Grounding)

* **The Problem:** In early prototypes, when asked to write an executive report about a competitor, LLMs would occasionally make up believable-sounding details or paraphrase competitor claims so heavily that you couldn't find where they came from. In competitive intelligence, citing a fake price or non-existent feature can ruin business strategy.
* **Why It Happened (In Plain English):** Generative AI is designed to sound plausible, not necessarily to be factually accurate. Unless you force it to prove where every claim comes from, it will fill in gaps using its imagination.
* **How We Fixed It:** We created a strict "Critic / Verifier" node with a mathematical **Evidence Grounding Accuracy ($EGA$)** threshold:
  1. The AI cannot simply say *"Competitor lowered prices."* It must extract the exact, verbatim quote from the raw website snapshot.
  2. The Critic agent searches the raw snapshot text for the exact character positions (`char_offset_start` to `char_offset_end`). If the quote cannot be found word-for-word in the actual web page, it is flagged as ungrounded.
  3. If $EGA < 85\%$, the finding is automatically downgraded or rejected.
  4. The Proposal Generator has an absolute firewall: if an insight is not `VERIFIED`, the system refuses to generate an executive proposal from it.
* **The Lesson:** You cannot blindly trust LLM summaries for business decisions. High-stakes AI applications must enforce mechanical proof (exact character offsets in source documents) before any claim is accepted.

---

### 7. The Expensive Cloud API Trap (Zero-Cost Operation)

* **The Problem:** Most modern AI tutorials assume you have unlimited budget for paid API keys (like OpenAI GPT-4). If an API key expires, has a billing limit, or if you lose internet access on a train, the entire application stops working and automated tests fail.
* **Why It Happened (In Plain English):** Hardcoding third-party cloud APIs ties your software to a single paid vendor. If the evaluator or teammate testing your code doesn't have an active paid account, they can't even evaluate your project.
* **How We Fixed It:** We implemented an **LLM Provider Factory** governed by a zero-paid-API mandate:
  - **Deterministic Mock Model (Default):** Runs completely offline with zero internet and zero API keys. It inspects diffs and generates fully grounded, mathematically verified findings and 7-section proposals for test suites and offline demos.
  - **Free-Tier Cloud Providers:** Plug-and-play support for Groq (blazing fast Llama-3.3) and Google Gemini 1.5 Flash (free tier).
  - **Local Models:** Native support for running local open-source models via Ollama.
* **The Lesson:** Software should always be able to run and demonstrate its core value for free out-of-the-box. Premium cloud APIs should be an optional upgrade, not a prerequisite for basic functionality.

---

## 📈 System Health & Verification Summary

Every single component across the entire stack is backed by rigorous automated testing:

| Test Suite | Focus Area | Result |
|---|---|:---:|
| `test_auth.py` | JWT authentication, bcrypt hashing, token expiration | ✅ 100% Pass |
| `test_workspaces.py` | Multi-tenant isolation, workspace permissions, CRUD | ✅ 100% Pass |
| `test_competitors.py` | Competitor profiles, source URL registration | ✅ 100% Pass |
| `test_adapters.py` | HTML extraction, RSS 2.0 / Atom 1.0 normalization | ✅ 100% Pass |
| `test_diff_engine.py` | Myers diff algorithm, SHA-256 change hashing | ✅ 100% Pass |
| `test_classifier.py` | Noise suppression, pricing & feature categorization | ✅ 100% Pass |
| `test_scans_api.py` | Concurrent background scanning & error tolerance | ✅ 100% Pass |
| `test_changes_api.py` | Filterable changes feed, diff retrieval endpoints | ✅ 100% Pass |
| `test_adversarial_challenger*.py` | Malformed XML, SQL injection attempts, token tampering | ✅ 100% Pass |
| `test_agent_pipeline_integration.py` | LangGraph Researcher, Impact Analyzer, Critic & Proposals | ✅ 100% Pass |
| **Total Test Count** | **Full End-to-End Suite** | **✅ 210 / 210 Passed** |

---

## 🚀 Key Takeaways & The Road Ahead

TradeCraft demonstrates that modern AI applications are most powerful not when an LLM is used as an isolated chatbot, but when it is embedded into a **disciplined engineering pipeline**:
- **Deterministic foundations first:** Reliable web scraping, clean diffs, and heuristic filters handle 90% of the heavy lifting for pennies.
- **Verification over generation:** Agents must be checked by other agents, and claims must point to concrete character offsets in source files.
- **Developer ergonomics matter:** Software that boots smoothly without fragile external dependencies is software that gets built, tested, and shipped.
