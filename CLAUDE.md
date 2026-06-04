# SciML Paper Scraper — Project Context & Requirements

## What this is

A **daily new-paper scraper/curator** for **Scientific Machine Learning (SciML)**,
**AI for Scientific Computing**, and **AI for Applied Math**. Think *HuggingFace Daily
Papers*, but narrowed to **only** these fields — NOT the broad "AI for Science" umbrella.

Dual purpose:
1. A personal tool the author reads every morning.
2. A public open-source product shipped on GitHub for the community.

## Hard constraints

- **$0 cost.** No paid API usage. Must run for free, indefinitely.
- **Runs in the cloud, daily, unattended** — must keep working when the laptop is closed.
  Target runner: **GitHub Actions scheduled workflow** (free *and unlimited* for public
  repos). No always-on server, no VPS.
- **Open-source friendly:** ideally minimal/no secrets so anyone can fork and run it.
- **Keep it simple and clean.** Minimal options/config, no premature abstraction, no
  provider-swapping layers. Gemini Flash is the only model. One source of truth for the
  taxonomy/keywords/categories. Favor a few small, focused modules over flexibility nobody asked for.

## Decisions locked in

- **Runner:** GitHub Actions cron (daily). Output is a static artifact committed back to
  the repo / deployed from it.
- **Output formats (v1):** a **web page** like HF Daily Papers — browsable, archived by date
  (`/2026-06-03`, …) — plus an **RSS/Atom feed** so it's subscribable. A **daily email
  digest is deferred** to a later version.
  - README-only output was **rejected** (becomes an unscrollable wall with many papers).
- **v1 = comprehensive daily filtered index. NO ranking / "Top picks."** Ranking is
  explicitly **deferred** to a later version (no community upvotes on day 0; ranking would
  need LLM relevance scoring / personal-interest match / trending signals — out of scope for v1).
- **Scope style:** *wide net within the methods space, with per-paper subfield tags*
  ("wide but tag subfields"). Each paper gets one or more subfield tags so the site can
  filter/collapse by subfield.
- **Classification:** the latest free-tier **Google Gemini Flash** (currently **Gemini 3.5
  Flash**; the exact model name lives in the one config file, so version bumps are a one-line
  change). The **one and only** LLM — not swappable, no provider abstraction (keep it simple).
  **No embeddings.** Stays within the free tier at ~60–180 papers/day → $0. (LLM task spec below.)
- **API key handling:** key is **never committed**. Stored as a **GitHub Actions encrypted
  secret** (`GEMINI_API_KEY`), injected at runtime via `env: ${{ secrets.GEMINI_API_KEY }}`,
  auto-masked in logs. Forks/outside PRs do not receive it. Local runs read it from a
  **`.gitignore`d `.env`** file. (Add `.env` to `.gitignore` from day one.)
- **Gray-zone rule (method applied to a science domain):** **include on any methods overlap.**
  Keep a paper if it touches SciML / applied-math / scientific-computing **methods** at all,
  even when demonstrated on a domain (e.g. a neural operator tested on weather). The broad
  "AI for Science" *domain* papers (bio/protein, materials, chemistry, drug discovery,
  climate, medicine) are **out of scope** unless a SciML/applied-math method is the actual
  contribution.
- **Sources (v1):** **arXiv** (free API) over a **generous but specific category set** —
  cs.LG, cs.NA, cs.AI, cs.CL, cs.CE, stat.ML, math.NA, math.OC, math.DS, math.AP, math.PR, math-ph,
  physics.comp-ph, physics.flu-dyn, eess.SY (editable in `config.ARXIV_CATEGORIES`). **Measured live
  2026-06: ~400–600 papers/day** across this set. Precision comes from the **keyword prefilter +
  LLM**, not from narrowing categories further. **+ OpenReview** (ICLR/NeurIPS submissions).
  Cross-source **dedup** required. More categories/sources later.
- **Tech stack:** **Python** end-to-end — fetch + prefilter + LLM classify + render.
  **Jinja2** templates → **static HTML** deployed free on **GitHub Pages**. Light vanilla JS
  for client-side tag filtering/search. One language, cohesive, $0 hosting.

## Deferred to later versions (explicitly out of v1)

- **Ranking / "Top picks"** — LLM relevance scoring, personal-interest match, trending signals.
- **Daily email digest** — add a free send path later (e.g. Resend free tier, or Gmail SMTP
  app password), reusing the curated daily set. Must stay short + link to the site.
- **More sources** — Semantic Scholar, Papers with Code, etc., beyond arXiv + OpenReview.

## In-scope subfield taxonomy (the classifier's target tags — editable config)

- **Operator learning** — neural operators (FNO, DeepONet, graph/transformer operators),
  geometry-aware operators on manifolds
- **PDE foundation models** — pretrained-on-many-PDEs, fine-tunable (Poseidon, SPUS, CompNO, P3)
- **Physics-informed ML** — PINNs, PINO, deep energy methods, + numerical analysis/convergence
  theory of them
- **Generative models for simulation** — diffusion models for PDEs/turbulence, probabilistic
  surrogates, physics-informed (spectral) diffusion
- **Differentiable simulation** — differentiable physics, hybrid physics–neural surrogates
- **ML-accelerated numerical methods** — learned/meta-solvers, accelerating legacy solvers,
  reduced-order modeling
- **Equation discovery & dynamical systems** — symbolic regression, **SINDy**, neural ODEs,
  Koopman/DMD, operator discovery
- **LLMs & agents for math / sci-computing** — LLM agents for PDEs & scientific computing,
  self-evolving scientific agents, autoformalization & LLM theorem proving (AlphaProof-style),
  LLMs generating solver code
- **Mathematical analysis of LLMs / neural nets** (tag `mathematical-analysis-of-llm`) —
  applied-math theory of LLMs: training & attention dynamics, mean-field / interacting-particle
  views, expressivity, approximation, convergence, stability, generalization bounds, geometry of
  in-context learning. IN for the *mathematical* content, **not** the LLM topic. (Refs:
  arXiv 2312.10794, 2512.01868, 2410.05218, 2410.02724.)
- **UQ & inverse problems** — uncertainty quantification, Bayesian SciML, inverse problems,
  data assimilation
- **Foundations** — Gaussian processes for scientific computing, AI–HPC hybridization

### Out of scope (unless the contribution is a SciML/applied-math method)
Domain "AI for Science": biology/protein, materials, chemistry, drug discovery, climate/weather,
medicine. Also generic ML/LLM papers with no scientific-computing/applied-math angle.

## LLM task spec (Gemini Flash — the only LLM call)

The LLM has **one job**: classify a single candidate paper (already past the cheap prefilter).
No summarizing, ranking, or rewriting.

- **Input per request (one paper):** `title`, `abstract`, `categories` (arXiv cats / OpenReview venue).
- **Fixed instruction (system prompt, identical every call):** scope definition + gray-zone rule
  ("include on any methods overlap") + out-of-scope domain list + the **allowed subfield tag list**
  (model must pick only from these).
- **Output (Gemini JSON mode — guaranteed parseable):**
  ```json
  { "in_scope": true,
    "tags": ["operator-learning", "pde-foundation-models"],
    "reason": "Introduces a neural-operator architecture pretrained across PDE families." }
  ```
  `tags` empty when `in_scope` is false. `reason` = one sentence, reused as the site card blurb +
  debugging aid.
- **Execution (batched):** classify **N papers per request** (batch size in config, e.g. 20) — the
  user message is a numbered list, the output a JSON **array** of `{id, in_scope, tags, reason}`.
  Latency is irrelevant to us, so batching is pure upside: it cuts requests ~N× (≈100–200
  candidates/day → ~5–10 requests). JSON mode + array response schema for reliable parsing.
  Sequential with a small delay; 429-aware stop/resume. (See "BATCH MODE" in `prompts/classify.md`.)

## LLM request budget (stay under the free tier)

Gemini Flash free tier (2026): ~**1,500 requests/day**, **10 RPM**, 250K tokens/min (per project,
resets midnight Pacific). The design keeps daily calls far below that:

- **Classify once, ever.** Persist each classification keyed by paper ID (arXiv id / OpenReview id).
  Daily runs call the LLM only on *new, unseen* papers — overlapping categories and re-runs never
  re-classify. Steady-state requests = new papers that day.
- **Prefilter before the LLM.** Category + keyword prefilter cuts the firehose ~5–10× before any
  API call; only plausible candidates are classified.
- **Typical day (measured): ~400–600 fetched → ~100–200 candidates, batched ~20/request → ~5–10
  requests** (<1% of the 1,500/day quota). Even a conference spike of ~2,000 candidates → ~100
  requests, far under 1,500.
- **Safety valve for conference-deadline spikes** (OpenReview can dump thousands at once): a daily
  backstop cap `MAX_LLM_REQUESTS_PER_DAY ≈ 1200`. Overflow is **carried to the next day** (unseen
  papers stay queued; a daily feed loses nothing by deferring). Batching makes this rarely relevant,
  but it stays as a hard backstop. Log how many were deferred.
- **RPM pacing:** ~6 s between calls (≈10 RPM) so the per-minute limit is never tripped.
- **Hard guarantee (not just an estimate):** the runner counts calls and stops at the cap, and
  also catches HTTP 429 (quota/rate-limit) responses — halting cleanly, marking the rest *pending*,
  resuming next run. The quota **cannot** be exceeded by construction; a spike only delays papers.

**Daily volume funnel (measured 2026-06):** ~400–600 papers *fetched* from the generous category
set (cheap API pulls, seconds) → ~400–600 *new after dedup + seen-filter* → ~100–200 *candidates*
(keyword prefilter) → **batched ~20/request → ~5–10 LLM requests** → ~40–120 *in-scope* shown on
the site, each tagged so you can narrow to the subfields you care about. Total runner time ≈ 5–10
min/day. Only the request count costs quota, and batching keeps it at <1% of the daily free limit.

The prompt itself lives in `prompts/classify.md` (approved separately).

## Pipeline shape (high level)

`fetch (arXiv + OpenReview) → dedup → cheap prefilter (categories + keywords) → LLM classify
in/out + assign subfield tags → store daily set → render static web page (archived by date) +
RSS feed → deploy to GitHub Pages` — all orchestrated by a daily GitHub Actions cron, at $0.
