# SciML Daily — UI Redesign + Two-Sentence Summary (Design)

Date: 2026-06-05
Status: Approved (pending spec review)

## 1. Goal

Rebuild the public site to feel like HuggingFace Daily Papers: a full-width, responsive
**grid of paper cards**, a **date strip** to browse days (defaulting to the latest), and a
separate **Search** tab. Replace the current narrow single-column list, the three nav tabs
(Today / Archive / RSS), and RSS entirely. Additionally, change the LLM output from a
one-sentence `reason` to a **two-sentence summary** shown on each card.

This intentionally overrides several decisions previously locked in `CLAUDE.md` (RSS feed
output, archive page, "classify only — no summarizing"). User instructions take precedence;
`CLAUDE.md` and `README.md` will be updated to match.

## 2. Non-goals (unchanged from project scope)

- No ranking / "top picks", no upvotes, comments, or any interaction. Display-only site.
- No PDF thumbnail previews (arXiv has no free thumbnail API; real screenshots need build-time
  PDF download + render, which conflicts with the low-cost/simple mandate and risks arXiv 429s).
- No email digest, no new sources, no embeddings.

## 3. Architecture: static single-page app

Move from per-day server-rendered HTML to **one shell page + one data file**, rendered client-side.

`build.py` emits exactly:

- `docs/index.html` — the single shell (header with Daily/Search tabs; empty containers filled by JS).
- `docs/data.json` — `{ "tags": { slug: {name, color} }, "papers": [ ... ] }`.
- `docs/static/` — copied `style.css` + `app.js`.

Each paper object in `data.json` ships only the fields the UI needs:

```json
{ "id": "arxiv:2606.04018", "title": "...", "authors": ["..."],
  "tags": ["physics-informed-ml", "foundations"], "url": "https://arxiv.org/abs/...",
  "source": "arXiv", "summary": "...", "added": "2026-06-04" }
```

Dropped from the shipped JSON: `categories`, `published`, `in_scope` (not displayed). `reason`
is renamed to `summary` (see §6).

`app.js` fetches `data.json` once, holds papers in memory, and derives both views:
- date strip = unique `added` values, ascending, latest selected by default;
- Daily view = papers where `added == selected date`;
- Search view = all papers filtered by query + selected tags.

**Deleted:** `templates/archive.html`, `templates/feed.xml`, `docs/archive.html`,
`docs/feed.xml`, `docs/day/*.html`, and all RSS generation in `build.py` (and `RSS_COUNT` use).

**Trade-off accepted:** the page is JS-rendered (no no-JS fallback, weaker SEO) — acceptable for
this app-like experience. `data.json` is tiny now (~109 papers). If it ever exceeds a few MB it
can later split into a light index + per-day files; that is YAGNI for v1 and not built now.

**Local preview note:** `fetch('data.json')` requires an HTTP server (not `file://`). Preview with
`python -m http.server` from `docs/`. (The current site already uses absolute URLs, so this is no
regression.)

## 4. Layout & visual

- **Full-width** container (max ~1500px, generous padding) — replaces the cramped 740px column.
- **Responsive card grid:** `grid-template-columns: repeat(auto-fill, minmax(330px, 1fr))` with a
  gap. Many cards abreast on wide screens, collapsing to 1–2 on narrow/tall windows automatically.
- **Sans-serif throughout:** single modern family **Plus Jakarta Sans** (Inter / system-ui
  fallback). Drops the serif `Newsreader`.
- **Auto light/dark** via `prefers-color-scheme` (keep existing token approach, retune).
- Removed filler copy (the tagline sentence, footer tagline, etc.). Header = brand + two tabs only.

## 5. Components

### 5.1 Paper card (no preview, no reason)
Shows, top to bottom: a thin top accent colored by the first tag; **title** (links to the arXiv
abstract page, `target="_blank"`); the **two-sentence summary**; **tag pills** (colored per
`config.TAGS`); a meta row with an **arXiv source badge**, **authors** (show up to **10**, then
"+N" for the remainder), and an **Abstract** toggle button that expands/collapses the full
abstract inline. No upvotes,
no comments, no reason/notes.

### 5.2 Navigation — two tabs, no reload
Top bar: `SciML Daily` brand · **Daily** | **Search**. Switching tabs toggles which view is
visible (client-side). Lightweight **hash routing** so tabs/dates are shareable and the back
button works: e.g. `#search` for the Search tab, and the selected date encoded in the hash for
Daily (default/empty hash = Daily at latest date).

### 5.3 Daily view (default)
- A horizontal, scrollable **date strip**: dates in chronological order, **latest at the right and
  selected by default**, auto-scrolled into view. Clicking a date swaps the grid instantly.
- Above the grid: the selected day's full date (e.g. "Thursday, June 5, 2026") and paper count.
- **No search box on this tab.**
- Strip is scrollable; jumping far back is a scroll. Acceptable for v1 (future: month jump).

### 5.4 Search view (separate tab)
- A **search input** matching **titles + authors**.
- **Multi-select tag filter pills** with **OR** semantics: selecting tags shows papers in *any*
  selected subfield; no selection = all tags. Pills reflect `config.TAGS` colors.
- Results: card grid across **all dates**, newest first, each card showing its date.
- Empty state when nothing matches.

## 6. LLM change: two-sentence summary (replaces `reason`)

The LLM now classifies **and** summarizes (overrides "no summarizing" in `CLAUDE.md`).

- **`prompts/classify.md`:** rename output field `reason` → **`summary`**, defined as exactly
  **two sentences**: (1) the specific problem this paper investigates; (2) the key method /
  innovation. Instruction must demand: be specific, use the paper's own terminology, surface the
  most important points of *this* paper — **not background**. Update: the system-instruction line
  that forbids summarizing, the Output spec, the BATCH-MODE I/O spec, and all 11 worked examples
  (rewrite each `reason` into a two-sentence `summary`). For out-of-scope papers `summary` may be a
  brief throwaway note (never displayed) so a debug trail remains.
- **`classify.py`:** `_apply` reads `summary` instead of `reason`; raise the cap from `[:300]` to
  about `[:600]` to fit two sentences. Field stored on each paper is `summary`.
- **No live backfill.** Existing 109 papers keep their old one-sentence text, migrated by a pure
  **local rename** of `reason` → `summary` in `data/papers.json` (no API call). New papers get the
  proper two-sentence summary going forward. `build.py` also falls back to `summary or reason or ""`
  when shipping `data.json`, for safety.

## 7. Fonts & theme

- Load **Plus Jakarta Sans** (weights 400/500/600/700) from Google Fonts; fallback
  `Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. Remove the Newsreader import.
- Keep `prefers-color-scheme` light/dark with retuned tokens for a modern, clean, low-distraction look.

## 8. Housekeeping

- **`CLAUDE.md`:** update Output-formats decision (date-strip + search SPA; RSS removed; no archive
  page) and the LLM task spec / funnel text (classify **+ two-sentence summary**).
- **`README.md`:** update any RSS/archive/structure references to match.
- **`config.py`:** keep `SITE_TAGLINE` only for the HTML `<meta name="description">` (SEO) — it is
  **removed from all on-page display**; remove `RSS_COUNT` (no longer used). Keep `TAGS` as the
  single source of truth.
- **Tests:** update `tests/test_build.py` to assert the new outputs (`index.html`, `data.json` shape)
  instead of `archive.html` / `feed.xml` / per-day pages. Update `tests/test_classify.py` if it
  asserts on `reason`. Keep the suite green.
- **`.github/workflows/daily.yml`:** verify it still works (same build entry point); adjust only if
  it references removed outputs.

## 9. File-by-file change list

- `build.py` — emit `index.html` + `data.json` + static; delete archive/feed/per-day/RSS logic.
- `templates/page.html` — becomes the SPA shell (header, tabs, empty view containers).
- `templates/archive.html`, `templates/feed.xml` — deleted.
- `static/style.css` — full rewrite: full-width grid, cards, date strip, tabs, search, Plus Jakarta Sans.
- `static/app.js` — rewrite: fetch `data.json`, render daily + search views, date strip, tag filter,
  abstract toggle, hash routing.
- `prompts/classify.md` — `reason` → two-sentence `summary` (instruction, output, batch, examples).
- `classify.py` — read/store `summary`, raise length cap.
- `data/papers.json` — local rename `reason` → `summary` (no API).
- `config.py` — drop `RSS_COUNT` use; tagline no longer on-page.
- `CLAUDE.md`, `README.md` — reflect new output formats + LLM summary.
- `tests/test_build.py`, `tests/test_classify.py` — update expectations.
- Remove stale generated files: `docs/archive.html`, `docs/feed.xml`, `docs/day/*.html`.

## 10. Edge cases

- No papers at all / no papers for a date → friendly empty state.
- A paper whose first tag isn't in `config.TAGS` → neutral accent fallback.
- Long author lists → show up to 10, then "+N".
- Missing `summary` → fall back to `reason`, then empty.
- Date strip with many days → horizontal scroll, latest auto-scrolled into view.
