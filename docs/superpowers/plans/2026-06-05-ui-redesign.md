# SciML Daily UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the public site as a full-width, HuggingFace-style responsive card grid with a date-strip browser and a separate Search tab, and change the LLM output from a one-sentence `reason` to a two-sentence `summary` shown on each card.

**Architecture:** Move from per-day server-rendered HTML + RSS to a static single-page app: `build.py` emits one `index.html` shell plus a `data.json` payload; `static/app.js` fetches it once and renders both the Daily view (filtered to the selected date) and the Search view client-side. RSS, archive page, and per-day pages are removed.

**Tech Stack:** Python 3.11, Jinja2 (shell only), vanilla JS (no framework), CSS (Grid + `prefers-color-scheme`), Plus Jakarta Sans (Google Fonts), pytest, DeepSeek V4 Flash (classifier prompt only).

**Spec:** `docs/superpowers/specs/2026-06-05-ui-redesign-design.md`

**Conventions in this repo:** modules are flat at the repo root (`build.py`, `classify.py`, `config.py`, `main.py`); tests live in `tests/` and import modules directly (e.g. `import build`); run tests with `pytest -q`. Commit messages end with the `Co-Authored-By` trailer.

---

## Task 1: Classifier emits a two-sentence `summary` instead of `reason`

**Files:**
- Modify: `classify.py` (the `_apply` function)
- Test: `tests/test_classify.py`

- [ ] **Step 1: Update the existing tests to expect `summary`**

In `tests/test_classify.py`, the mock generators currently return `"reason"` keys and nothing asserts on them. Switch the mocks to `"summary"` and add an assertion that the summary is captured. Replace the body of `test_classify_validates_and_drops_unknown_tags` with:

```python
def test_classify_validates_and_drops_unknown_tags():
    def gen(instr, msg):
        return ('[{"id":1,"in_scope":true,"tags":["operator-learning","nope"],"summary":"Problem. Method."},'
                '{"id":2,"in_scope":false,"tags":[],"summary":"out"}]')
    out, used = classify.classify(papers(2), gen, instruction="x", sleep=lambda s: None)
    assert out[0]["in_scope"] is True and out[0]["tags"] == ["operator-learning"]
    assert out[0]["summary"] == "Problem. Method."
    assert out[1]["in_scope"] is False and out[1]["tags"] == []
    assert used == 1
```

Then, in the other three mocks in this file, rename the JSON key `"reason"` to `"summary"`:
- `test_classify_maps_by_position_when_no_id`: change `"reason":"a"` → `"summary":"a"` and `"reason":"b"` → `"summary":"b"`.
- `test_classify_parses_fenced_and_wrapped_json`: change `"reason":"r"` → `"summary":"r"`.
- `test_classify_respects_cap`: change `"reason":"r"` → `"summary":"r"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_classify.py -q`
Expected: `test_classify_validates_and_drops_unknown_tags` FAILS on `assert out[0]["summary"] == "Problem. Method."` (KeyError or empty), because `_apply` still writes `reason`, not `summary`.

- [ ] **Step 3: Make `_apply` write `summary`**

In `classify.py`, replace the `_apply` function:

```python
def _apply(item, p):
    valid = set(config.TAGS)
    in_scope = bool(item.get("in_scope"))
    tags = [t for t in (item.get("tags") or []) if t in valid] if in_scope else []
    return {**p, "in_scope": in_scope, "tags": tags, "summary": str(item.get("summary", ""))[:600]}
```

(Two sentences need more room than the old one-sentence `[:300]` cap, so it is raised to `[:600]`. The field is renamed `reason` → `summary`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_classify.py -q`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add classify.py tests/test_classify.py
git commit -m "feat: classifier returns two-sentence summary (replaces reason)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Rewrite the classifier prompt to produce the two-sentence summary

**Files:**
- Modify: `prompts/classify.md`
- Test: `tests/test_classify.py::test_load_instruction` (must still pass; no change needed)

This task is prose edits to the prompt. `classify.load_instruction()` slices the text between `## SYSTEM INSTRUCTION` and `## USER MESSAGE`, so those two headers must remain. The required `summary` definition: **exactly two sentences — (1) the specific problem the paper investigates; (2) the key method / innovation; be specific, use the paper's own terminology, surface the most important points of *this* paper, not background.**

- [ ] **Step 1: Loosen the "do not summarize" instruction**

In `prompts/classify.md`, find this line (around line 16-18):

```
Your only job: given one paper's title, abstract, and source categories, decide whether it
belongs in the feed and, if so, assign subfield tags. Do not summarize, rank, or rewrite.
Be decisive.
```

Replace it with:

```
Your job: given one paper's title, abstract, and source categories, decide whether it belongs in
the feed, assign subfield tags, and write a two-sentence summary of the paper. Do not rank or
editorialize. Be decisive and specific.
```

- [ ] **Step 2: Replace the Output section**

Find the `### Output` section (around lines 83-96) and replace everything from `### Output` up to (but not including) `### Examples` with:

````
### Output
Return ONLY a JSON object (no markdown fences, no commentary) with this exact shape:

```json
{
  "in_scope": true,
  "tags": ["operator-learning"],
  "summary": "First sentence: the specific problem this paper investigates. Second sentence: the key method or innovation it introduces."
}
```

- `tags` MUST be `[]` when `in_scope` is `false`.
- `tags` MUST contain only slugs from the allowed list above.
- `summary` is **exactly two sentences**: (1) the specific problem/question this paper tackles,
  and (2) the key method, model, or innovation it contributes. Be concrete and use the paper's own
  terminology (name the method, architecture, equation class, etc.). State what is novel about THIS
  paper — do not describe general background or the field. When `in_scope` is `false`, `summary`
  may instead be a brief note on why it is out of scope (it is never displayed).
````

- [ ] **Step 3: Rewrite the 11 examples to use two-sentence `summary`**

Find the `### Examples` section (around lines 98-144) and replace each example's `"reason": "..."` with a `"summary": "..."`. Use these exact replacements (problem sentence + method sentence; out-of-scope keep a short note):

```
1. → {"in_scope": true, "tags": ["operator-learning"], "summary": "Solving families of parametric PDEs with classical solvers is expensive when the geometry varies. The paper introduces a geometry-aware Fourier neural operator that conditions on mesh geometry to map parameters to solutions faster than classical solvers."}

2. → {"in_scope": true, "tags": ["operator-learning"], "summary": "Numerical weather prediction is costly to run at scale. The paper trains a graph neural operator to emulate atmospheric dynamics, achieving large speedups over classical NWP while remaining a methods contribution despite the weather application."}

3. → {"in_scope": false, "tags": [], "summary": "Out: applies an off-the-shelf transformer to a biology prediction task with no scientific-computing or applied-math method."}

4. → {"in_scope": false, "tags": [], "summary": "Out: generic RLHF chat-assistant alignment with no applied-math or scientific-computing angle."}

5. → {"in_scope": true, "tags": ["llm-agents-for-sci-computing", "equation-discovery-dynamical-systems"], "summary": "Deriving and solving symbolic PDEs by hand is labor-intensive. The paper builds a multi-agent LLM system that proposes, manipulates, and solves PDEs symbolically as a scientific-computing workflow."}

6. → {"in_scope": true, "tags": ["mathematical-analysis-of-llm"], "summary": "It is unclear how floating-point rounding errors accumulate inside attention. The paper performs a numerical-analysis of the attention mechanism and derives rounding-error stability bounds, an in-scope mathematical result rather than an LLM application."}

7. → {"in_scope": true, "tags": ["mathematical-analysis-of-llm"], "summary": "The dynamics of how Transformers process tokens over depth are poorly understood mathematically. The paper models attention as an interacting particle system and uses dynamical-systems theory to show that token clusters emerge over long time."}

8. → {"in_scope": true, "tags": ["mathematical-analysis-of-llm"], "summary": "The continuum behavior of attention at scale lacks a rigorous description. The paper takes the mean-field limit of attention as an interacting particle system, connecting it to Wasserstein gradient flows and Kuramoto synchronization and identifying a clustering phase transition."}

9. → {"in_scope": true, "tags": ["mathematical-analysis-of-llm"], "summary": "How LLMs perform in-context density estimation is not well characterized. The paper analyzes the geometry of in-context trajectories via Intensive PCA and interprets them as an adaptive-bandwidth kernel density estimator."}

10. → {"in_scope": true, "tags": ["mathematical-analysis-of-llm"], "summary": "Generalization guarantees for autoregressive LLMs are scarce. The paper formalizes autoregressive transformers as Markov chains on a finite state space and derives pre-training and in-context generalization bounds."}

11. → {"in_scope": false, "tags": [], "summary": "Out: empirical LLM pretraining/engineering (loss-vs-compute curves, data mixing) with no applied-math or scientific-computing theory."}
```

Keep each example's existing Title/Abstract lines; only the `→ {...}` result line changes.

- [ ] **Step 4: Update the BATCH MODE output spec**

Find the BATCH MODE output block (around lines 183-189) and replace the JSON array example and the line after it:

```
- **Output** — a JSON **array**, one object per input paper:
  ```json
  [ { "id": 1, "in_scope": true,  "tags": ["operator-learning"], "summary": "Problem sentence. Method sentence." },
    { "id": 2, "in_scope": false, "tags": [], "summary": "Out: brief reason." } ]
  ```
  `id` echoes the input index. Same `in_scope` / `tags` / `summary` contract as the single-paper case.
```

- [ ] **Step 5: Verify the prompt still loads and contains no stray `reason`**

Run:
```bash
pytest tests/test_classify.py::test_load_instruction -q
grep -n '"reason"' prompts/classify.md || echo "no stray reason keys"
grep -c '"summary"' prompts/classify.md
```
Expected: the test PASSES; `grep` for `"reason"` prints `no stray reason keys`; the `"summary"` count is ≥ 13 (output spec + 11 examples + batch example).

- [ ] **Step 6: Commit**

```bash
git add prompts/classify.md
git commit -m "feat: prompt produces two-sentence summary (problem + method)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Migrate `data/papers.json` — rename `reason` → `summary` (no API)

**Files:**
- Modify: `data/papers.json`

The 109 stored papers have `reason` but no `summary`. Per the spec, do a pure local rename so the field is consistent (their existing one-sentence text becomes the summary). No DeepSeek call.

- [ ] **Step 1: Rename the field in place**

Run:
```bash
python3 -c "
import json, pathlib
f = pathlib.Path('data/papers.json')
papers = json.loads(f.read_text(encoding='utf-8'))
for p in papers:
    if 'summary' not in p:
        p['summary'] = p.pop('reason', '')
    else:
        p.pop('reason', None)
f.write_text(json.dumps(papers, indent=1, ensure_ascii=False), encoding='utf-8')
print('migrated', len(papers), 'papers')
"
```
Expected: `migrated 109 papers`.

- [ ] **Step 2: Verify**

Run:
```bash
python3 -c "
import json
d = json.load(open('data/papers.json'))
assert all('summary' in p for p in d), 'missing summary'
assert not any('reason' in p for p in d), 'stray reason'
print('ok:', len(d), 'papers, all have summary, no reason')
"
```
Expected: `ok: 109 papers, all have summary, no reason`.

- [ ] **Step 3: Commit**

```bash
git add data/papers.json
git commit -m "data: rename reason -> summary in stored papers (local, no API)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Add the SPA shell template (`templates/page.html`)

**Files:**
- Modify: `templates/page.html` (full rewrite)

The new template is a static shell — no Jinja loops, only `{{ site_title }}` and `{{ tagline }}`.
The legacy templates `archive.html`/`feed.xml` are removed in Task 5 (so the build test there gets a
clean red). This task does not run `build` (the new `build.py` lands in Task 5).

- [ ] **Step 1: Rewrite `templates/page.html`**

Replace the entire contents of `templates/page.html` with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ site_title }}</title>
<meta name="description" content="{{ tagline }}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="static/style.css">
</head>
<body>
<header class="topbar">
  <a class="brand" href="#">{{ site_title }}</a>
  <nav class="tabs">
    <button class="tab active" data-view="daily">Daily</button>
    <button class="tab" data-view="search">Search</button>
  </nav>
</header>

<main>
  <section id="daily-view">
    <div class="datestrip" id="datestrip"></div>
    <div class="dayhead">
      <h1 id="day-title"></h1>
      <span class="count" id="day-count"></span>
    </div>
    <div class="grid" id="daily-grid"></div>
    <p class="empty" id="daily-empty" hidden>No papers for this date.</p>
  </section>

  <section id="search-view" hidden>
    <div class="searchbar">
      <input id="search-input" type="search" placeholder="Search titles and authors…" autocomplete="off">
    </div>
    <div class="pills" id="search-pills"></div>
    <p class="count" id="search-count"></p>
    <div class="grid" id="search-grid"></div>
    <p class="empty" id="search-empty" hidden>No papers match.</p>
  </section>
</main>

<script src="static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify the shell is a static shell with the expected hooks**

Run:
```bash
grep -c 'data-view="search"' templates/page.html
grep -q "{% for" templates/page.html && echo "WARN: stray Jinja loop" || echo "no Jinja loops (static shell ok)"
for id in datestrip daily-grid search-grid search-input search-pills; do grep -q "id=\"$id\"" templates/page.html || echo "MISSING #$id"; done; echo "ids checked"
```
Expected: `1`; `no Jinja loops (static shell ok)`; `ids checked` with no `MISSING` lines above it.

- [ ] **Step 3: Commit**

```bash
git add templates/page.html
git commit -m "feat: SPA shell template (Daily/Search tabs)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Rewrite `build.py` to emit `index.html` + `data.json`; remove legacy templates

**Files:**
- Modify: `build.py` (full rewrite)
- Delete: `templates/archive.html`, `templates/feed.xml`
- Test: `tests/test_build.py` (full rewrite)

Depends on Task 4 (the shell `templates/page.html` must already exist; the new `build.py` renders it).

- [ ] **Step 1: Rewrite the build test**

Replace the entire contents of `tests/test_build.py` with:

```python
# tests/test_build.py
import json
import build

PAPER = {"id": "arxiv:1", "source": "arXiv", "title": "Neural Operator X",
         "abstract": "We solve PDEs.", "authors": ["Jane Doe"],
         "categories": ["cs.LG"], "in_scope": True,
         "url": "https://arxiv.org/abs/1", "tags": ["operator-learning"],
         "summary": "PDEs are hard. We learn an operator.", "added": "2026-06-03"}

def test_build_writes_index_and_data(tmp_path):
    out = tmp_path / "docs"
    build.build([PAPER], out=out)

    assert (out / "index.html").exists()
    assert (out / "static" / "style.css").exists()
    assert (out / "static" / "app.js").exists()

    data = json.loads((out / "data.json").read_text(encoding="utf-8"))
    assert data["tags"]["operator-learning"]["name"] == "Operator Learning"
    assert data["tags"]["operator-learning"]["color"] == "#6366f1"

    assert len(data["papers"]) == 1
    p = data["papers"][0]
    assert p["id"] == "arxiv:1"
    assert p["summary"] == "PDEs are hard. We learn an operator."
    assert p["abstract"] == "We solve PDEs."
    assert p["added"] == "2026-06-03"
    # internal fields are not shipped to the browser
    assert "reason" not in p
    assert "in_scope" not in p
    assert "categories" not in p

def test_build_drops_legacy_outputs(tmp_path):
    out = tmp_path / "docs"
    build.build([PAPER], out=out)
    assert not (out / "feed.xml").exists()
    assert not (out / "archive.html").exists()
    assert not (out / "day").exists()

def test_build_summary_falls_back_to_reason(tmp_path):
    legacy = {**PAPER}
    del legacy["summary"]
    legacy["reason"] = "Legacy one-liner."
    out = tmp_path / "docs"
    build.build([legacy], out=out)
    data = json.loads((out / "data.json").read_text(encoding="utf-8"))
    assert data["papers"][0]["summary"] == "Legacy one-liner."

def test_build_empty_still_writes_index(tmp_path):
    out = tmp_path / "docs"
    build.build([], out=out)
    assert (out / "index.html").exists()
    data = json.loads((out / "data.json").read_text(encoding="utf-8"))
    assert data["papers"] == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_build.py -q`
Expected: FAIL — the current `build.build` still renders the legacy `archive.html`/`feed.xml`
templates and writes per-day pages while shipping `reason`, so there is no `data.json` of the
expected shape (and `feed.xml`/`archive.html` exist).

- [ ] **Step 3: Rewrite `build.py` and remove the legacy templates**

Replace the entire contents of `build.py` with:

```python
# build.py
import json
import shutil
from jinja2 import Environment, FileSystemLoader, select_autoescape
import config

def load_papers():
    if config.PAPERS_FILE.exists():
        return json.loads(config.PAPERS_FILE.read_text(encoding="utf-8"))
    return []

# Fields shipped to the browser in data.json. Internal fields (reason, in_scope,
# categories, published) are deliberately omitted; `summary` replaces `reason`.
CARD_FIELDS = ("id", "title", "authors", "tags", "url", "source", "abstract", "added")

def _card(p):
    card = {k: p.get(k) for k in CARD_FIELDS}
    card["summary"] = p.get("summary") or p.get("reason") or ""
    return card

def build(papers, out=None):
    out = out or config.DOCS
    out.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(config.TEMPLATES)),
                      autoescape=select_autoescape(["html", "xml"]))

    tags = {slug: {"name": n, "color": c} for slug, (n, c) in config.TAGS.items()}
    ordered = sorted(papers, key=lambda p: p.get("added", ""), reverse=True)  # newest first
    data = {"tags": tags, "papers": [_card(p) for p in ordered]}
    (out / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    page = env.get_template("page.html")
    (out / "index.html").write_text(
        page.render(site_title=config.SITE_TITLE, tagline=config.SITE_TAGLINE), encoding="utf-8")

    dst = out / "static"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(config.STATIC, dst)
```

Then remove the now-unused legacy templates:

```bash
git rm templates/archive.html templates/feed.xml
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_build.py -q`
Expected: PASS (all four tests). The shell `templates/page.html` (Task 4) and the existing
`static/style.css` / `static/app.js` are present, so the build renders and copies them.

- [ ] **Step 5: First real rebuild from migrated data**

Run:
```bash
python3 -c "import build; build.build(build.load_papers())"
python3 -c "
import json
d = json.load(open('docs/data.json'))
print('papers:', len(d['papers']), 'tags:', len(d['tags']))
assert 'reason' not in d['papers'][0] and 'summary' in d['papers'][0]
print('ok')
"
```
Expected: papers ~109, tags 11, `ok`. (The CSS/JS copied here are still the old ones; Tasks 6–7 rewrite them and rebuild again.)

- [ ] **Step 6: Commit**

```bash
git add build.py tests/test_build.py templates/archive.html templates/feed.xml docs
git commit -m "feat: build emits index.html + data.json; drop RSS/archive/per-day

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Rewrite `static/style.css` — full-width grid, cards, date strip, tabs, search

**Files:**
- Modify: `static/style.css` (full rewrite)

- [ ] **Step 1: Replace the stylesheet**

Replace the entire contents of `static/style.css` with:

```css
:root{
  --bg:#fafaf9; --surface:#ffffff; --ink:#16181d; --muted:#6b7280;
  --line:#e7e5e1; --accent:#4f46e5; --chip:#f1f0ee;
  --radius:14px; --shadow:0 1px 2px rgba(20,20,30,.04),0 6px 20px rgba(20,20,30,.06);
}
@media (prefers-color-scheme:dark){
  :root{--bg:#0d0f13; --surface:#161a20; --ink:#e8eaee; --muted:#98a0ad;
    --line:#242a33; --accent:#8b8cf5; --chip:#1d222b;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.35);}
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Plus Jakarta Sans",Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}

.topbar{position:sticky;top:0;z-index:30;display:flex;align-items:center;gap:24px;
  padding:14px clamp(16px,4vw,40px);background:color-mix(in srgb,var(--bg) 86%,transparent);
  backdrop-filter:saturate(150%) blur(10px);border-bottom:1px solid var(--line)}
.brand{font-weight:700;font-size:19px;letter-spacing:-.02em}
.tabs{display:flex;gap:4px;margin-left:auto;background:var(--chip);padding:4px;border-radius:999px}
.tab{border:0;background:none;color:var(--muted);font:inherit;font-weight:600;font-size:14px;
  padding:7px 18px;border-radius:999px;cursor:pointer;transition:color .15s,background .15s}
.tab:hover{color:var(--ink)}
.tab.active{color:var(--ink);background:var(--surface);box-shadow:var(--shadow)}

main{max-width:1500px;margin:0 auto;padding:24px clamp(16px,4vw,40px) 80px}

.datestrip{display:flex;gap:8px;overflow-x:auto;padding:6px 2px 14px;scrollbar-width:thin}
.datestrip::-webkit-scrollbar{height:6px}
.datestrip::-webkit-scrollbar-thumb{background:var(--line);border-radius:999px}
.date{flex:0 0 auto;border:1px solid var(--line);background:var(--surface);color:var(--muted);
  padding:8px 14px;border-radius:10px;font:inherit;font-size:13px;font-weight:600;cursor:pointer;
  white-space:nowrap;transition:color .15s,border-color .15s,background .15s}
.date:hover{color:var(--ink);border-color:var(--accent)}
.date.active{color:#fff;background:var(--accent);border-color:var(--accent)}

.dayhead{display:flex;align-items:baseline;gap:14px;margin:8px 0 20px;flex-wrap:wrap}
.dayhead h1{font-size:clamp(22px,3vw,30px);font-weight:700;letter-spacing:-.02em;margin:0}
.count{color:var(--muted);font-size:14px;font-weight:500}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px;align-items:start}

.card{display:flex;flex-direction:column;background:var(--surface);
  border:1px solid var(--line);border-top:3px solid var(--accent);
  border-radius:var(--radius);padding:18px 18px 16px;box-shadow:var(--shadow);
  transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-2px);box-shadow:0 2px 4px rgba(20,20,30,.05),0 12px 30px rgba(20,20,30,.1)}
.card h2{font-size:16.5px;font-weight:700;line-height:1.32;letter-spacing:-.01em;margin:0 0 8px}
.card h2 a:hover{color:var(--accent)}
.summary{margin:0 0 12px;font-size:14px;color:var(--ink);opacity:.86}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.tag{font-size:11.5px;font-weight:600;padding:3px 9px;border-radius:999px;
  color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent)}
.meta{display:flex;align-items:center;gap:10px;font-size:12.5px;color:var(--muted);
  flex-wrap:wrap;margin-top:auto}
.src{font-weight:700;letter-spacing:.03em;font-size:10.5px;text-transform:uppercase;
  padding:2px 7px;border-radius:6px;background:var(--chip);color:var(--muted)}
.card-date{font-weight:600}
.authors{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.abstract-toggle{align-self:flex-start;margin-top:12px;border:0;background:none;color:var(--accent);
  font:inherit;font-size:13px;font-weight:600;cursor:pointer;padding:0}
.abstract{margin:12px 0 0;padding-top:12px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13.5px;line-height:1.6}

.searchbar{margin:6px 0 14px}
#search-input{width:100%;padding:13px 16px;border:1px solid var(--line);border-radius:12px;
  background:var(--surface);color:var(--ink);font:inherit;font-size:15px;outline:none;
  transition:border-color .15s,box-shadow .15s}
#search-input:focus{border-color:var(--accent);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 22%,transparent)}
.pills{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.pill{border:1px solid var(--line);background:var(--surface);color:var(--muted);
  padding:7px 13px;border-radius:999px;font:inherit;font-size:13px;font-weight:600;cursor:pointer;
  transition:color .15s,background .15s,border-color .15s}
.pill:hover{color:var(--ink);border-color:color-mix(in srgb,var(--c,var(--accent)) 50%,var(--line))}
.pill.active{color:#fff;background:var(--c,var(--accent));border-color:var(--c,var(--accent))}

.empty{color:var(--muted);text-align:center;padding:60px 0;font-size:15px}

@media (max-width:520px){
  .grid{grid-template-columns:1fr}
  .topbar{gap:12px}
}
```

- [ ] **Step 2: Verify the file is valid CSS (balanced braces) and references the new font**

Run:
```bash
python3 -c "s=open('static/style.css').read(); assert s.count('{')==s.count('}'), 'unbalanced braces'; assert 'Plus Jakarta Sans' in s; assert 'minmax(330px' in s; print('css ok, braces:', s.count('{'))"
```
Expected: `css ok, braces: <N>`.

- [ ] **Step 3: Commit**

```bash
git add static/style.css
git commit -m "feat: redesign stylesheet — full-width card grid, date strip, tabs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Rewrite `static/app.js` — fetch data.json, render Daily + Search

**Files:**
- Modify: `static/app.js` (full rewrite)

Behavior contract:
- Fetch `data.json` (`{tags, papers}`), group papers by `added`, dates ascending (latest at right).
- Daily view: date strip (latest active, scrolled into view), full date heading + count, card grid.
- Search view: text input matches title + authors; multi-select tag pills with OR semantics ("All" clears); results across all dates, newest first, each card shows its date.
- Cards: title link (new tab), two-sentence summary, tag pills, meta row (arXiv badge, optional date, authors up to 10 then "+N"), Abstract toggle.
- Hash routing: `#search` → Search; `#YYYY-MM-DD` → that date; anything else → Daily at latest.

- [ ] **Step 1: Replace the script**

Replace the entire contents of `static/app.js` with:

```javascript
(function () {
  "use strict";

  var TAGS = {}, PAPERS = [], DATES = [], byDate = {}, latest = null;
  var searchTags = {};

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function asDate(d) { var p = d.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function fmtFull(d) {
    return asDate(d).toLocaleDateString("en-US",
      { weekday: "long", year: "numeric", month: "long", day: "numeric" });
  }
  function fmtShort(d) {
    return asDate(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  function plural(n) { return n + (n === 1 ? " paper" : " papers"); }

  function tagPill(slug) {
    var t = TAGS[slug];
    return t ? '<span class="tag" style="--c:' + t.color + '">' + esc(t.name) + "</span>" : "";
  }
  function accent(p) {
    var t = TAGS[(p.tags && p.tags[0]) || ""];
    return t ? t.color : "#94a3b8";
  }
  function authorsLine(a) {
    a = a || [];
    return a.length <= 10
      ? esc(a.join(", "))
      : esc(a.slice(0, 10).join(", ")) + " +" + (a.length - 10);
  }

  function card(p, showDate) {
    var tags = (p.tags || []).map(tagPill).join("");
    return '<article class="card" style="--accent:' + accent(p) + '">'
      + '<h2><a href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.title) + "</a></h2>"
      + (p.summary ? '<p class="summary">' + esc(p.summary) + "</p>" : "")
      + (tags ? '<div class="tags">' + tags + "</div>" : "")
      + '<div class="meta">'
        + '<span class="src">' + esc(p.source || "arXiv") + "</span>"
        + (showDate ? '<span class="card-date">' + esc(fmtShort(p.added)) + "</span>" : "")
        + '<span class="authors">' + authorsLine(p.authors) + "</span>"
      + "</div>"
      + '<button class="abstract-toggle" aria-expanded="false">Abstract</button>'
      + '<p class="abstract" hidden>' + esc(p.abstract) + "</p>"
      + "</article>";
  }

  function renderGrid(el, list, showDate) {
    el.innerHTML = list.map(function (p) { return card(p, showDate); }).join("");
  }

  function setTab(view) {
    [].forEach.call(document.querySelectorAll(".tab"), function (b) {
      b.classList.toggle("active", b.dataset.view === view);
    });
  }

  function renderStrip(active) {
    var strip = $("datestrip");
    strip.innerHTML = DATES.map(function (d) {
      return '<button class="date' + (d === active ? " active" : "")
        + '" data-date="' + d + '">' + esc(fmtShort(d)) + "</button>";
    }).join("");
    var act = strip.querySelector(".date.active");
    if (act) act.scrollIntoView({ inline: "center", block: "nearest" });
  }

  function showDaily(date) {
    if (!byDate[date]) date = latest;
    $("search-view").hidden = true;
    $("daily-view").hidden = false;
    setTab("daily");
    renderStrip(date);
    var list = byDate[date] || [];
    $("day-title").textContent = date ? fmtFull(date) : "No papers yet";
    $("day-count").textContent = plural(list.length);
    renderGrid($("daily-grid"), list, false);
    $("daily-empty").hidden = list.length !== 0;
  }

  function renderPills() {
    var box = $("search-pills");
    var none = Object.keys(searchTags).length === 0;
    var html = '<button class="pill' + (none ? " active" : "") + '" data-tag="">All</button>';
    Object.keys(TAGS).forEach(function (slug) {
      var t = TAGS[slug];
      html += '<button class="pill' + (searchTags[slug] ? " active" : "")
        + '" data-tag="' + slug + '" style="--c:' + t.color + '">' + esc(t.name) + "</button>";
    });
    box.innerHTML = html;
  }

  function runSearch() {
    var q = ($("search-input").value || "").trim().toLowerCase();
    var sel = Object.keys(searchTags);
    var list = PAPERS.filter(function (p) {
      var okTag = !sel.length || (p.tags || []).some(function (t) { return searchTags[t]; });
      if (!okTag) return false;
      if (!q) return true;
      var hay = (p.title + " " + (p.authors || []).join(" ")).toLowerCase();
      return hay.indexOf(q) !== -1;
    });
    $("search-count").textContent = plural(list.length);
    renderGrid($("search-grid"), list, true);
    $("search-empty").hidden = list.length !== 0;
  }

  function showSearch() {
    $("daily-view").hidden = true;
    $("search-view").hidden = false;
    setTab("search");
    renderPills();
    runSearch();
  }

  function route() {
    var h = (location.hash || "").replace(/^#/, "");
    if (h === "search") { showSearch(); return; }
    if (/^\d{4}-\d{2}-\d{2}$/.test(h) && byDate[h]) { showDaily(h); return; }
    showDaily(latest);
  }

  function wire() {
    document.addEventListener("click", function (e) {
      var tab = e.target.closest(".tab");
      if (tab) {
        location.hash = tab.dataset.view === "search" ? "search" : (latest || "");
        return;
      }
      var date = e.target.closest(".date");
      if (date) { location.hash = date.dataset.date; return; }

      var pill = e.target.closest(".pill");
      if (pill) {
        var slug = pill.dataset.tag;
        if (!slug) searchTags = {};
        else if (searchTags[slug]) delete searchTags[slug];
        else searchTags[slug] = true;
        renderPills();
        runSearch();
        return;
      }
      var tog = e.target.closest(".abstract-toggle");
      if (tog) {
        var ab = tog.parentNode.querySelector(".abstract");
        var open = !ab.hidden;
        ab.hidden = open;
        tog.setAttribute("aria-expanded", String(!open));
        tog.textContent = open ? "Abstract" : "Hide abstract";
      }
    });
    $("search-input").addEventListener("input", runSearch);
    window.addEventListener("hashchange", route);
  }

  function init(data) {
    TAGS = data.tags || {};
    PAPERS = data.papers || [];
    byDate = {};
    PAPERS.forEach(function (p) {
      (byDate[p.added] = byDate[p.added] || []).push(p);
    });
    DATES = Object.keys(byDate).sort();          // ascending → latest at the right
    latest = DATES.length ? DATES[DATES.length - 1] : null;
    wire();
    route();
  }

  fetch("data.json")
    .then(function (r) { return r.json(); })
    .then(init)
    .catch(function (e) {
      document.querySelector("main").innerHTML =
        '<p class="empty">Could not load papers. ' + esc(String(e)) + "</p>";
    });
})();
```

- [ ] **Step 2: Verify the script parses (Node syntax check if available) and contains the key handlers**

Run:
```bash
node --check static/app.js 2>/dev/null && echo "node syntax ok" || echo "node not available — skipping syntax check"
grep -q 'fetch("data.json")' static/app.js && grep -q 'slice(0, 10)' static/app.js && echo "handlers present"
```
Expected: `handlers present` (and `node syntax ok` if Node is installed).

- [ ] **Step 3: Rebuild the site with real data and sanity-check output**

Run:
```bash
python3 -c "import build; build.build(build.load_papers())"
python3 -c "
import json
d = json.load(open('docs/data.json'))
print('papers:', len(d['papers']), 'tags:', len(d['tags']))
print('sample summary:', d['papers'][0]['summary'][:60])
assert 'reason' not in d['papers'][0]
print('ok')
"
```
Expected: papers count ~109, tags 11, a sample summary prints, `ok`.

- [ ] **Step 4: Manual visual check (local server)**

Run (foreground; open the URL, then Ctrl-C):
```bash
echo "Open http://localhost:8000/  — verify: date strip (latest selected at right), card grid reflows on resize, Abstract toggles, Search tab filters by text + tags."
python3 -m http.server 8000 --directory docs
```
Expected: Daily view shows the latest date's cards in a responsive grid; switching to Search filters across all dates; tags multi-select; no RSS/Archive/Today tabs; no DeepSeek reason text on cards.

- [ ] **Step 5: Commit**

```bash
git add static/app.js
git commit -m "feat: SPA renderer — date strip, search, tag filter, abstract toggle

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Remove stale generated site files

**Files:**
- Delete: `docs/archive.html`, `docs/feed.xml`, `docs/day/*.html`

The build no longer produces these; remove the committed copies so the deployed site has no dead pages. (`docs/index.html`, `docs/data.json`, and `docs/static/` are the rebuilt outputs and stay.)

- [ ] **Step 1: Remove the legacy outputs**

Run:
```bash
git rm docs/archive.html docs/feed.xml
git rm -r docs/day
```
Expected: `archive.html`, `feed.xml`, and the `day/` directory removed.

- [ ] **Step 2: Verify the live docs dir is clean**

Run:
```bash
ls docs
test ! -e docs/feed.xml && test ! -e docs/archive.html && test ! -e docs/day && echo "legacy outputs gone"
test -f docs/index.html && test -f docs/data.json && echo "current outputs present"
```
Expected: `legacy outputs gone`; `current outputs present`.

- [ ] **Step 3: Commit**

```bash
git add -A docs
git commit -m "chore: remove stale archive/feed/per-day pages from docs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Housekeeping — config.py, CLAUDE.md, README.md

**Files:**
- Modify: `config.py`
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Remove the unused `RSS_COUNT` from `config.py`**

In `config.py`, delete this line (last line of the file):

```python
RSS_COUNT = 60
```

`SITE_TAGLINE` stays — it is still used for the HTML `<meta name="description">` (it is no longer shown on the page).

Also retire the now-stale RSS mention in the `SITE_URL` comment. Change the line:

```python
SITE_URL = "https://qile-j.github.io/sciml-daily"   # your Pages URL (used in links + RSS)
```

to:

```python
SITE_URL = "https://qile-j.github.io/sciml-daily"   # your Pages URL (canonical link)
```

(`SITE_URL` is no longer consumed by the build — the site uses relative asset paths — but it is kept as the canonical site address for reference.)

- [ ] **Step 2: Verify nothing references `RSS_COUNT`**

Run:
```bash
grep -rn "RSS_COUNT" --include=*.py . || echo "no RSS_COUNT references"
```
Expected: `no RSS_COUNT references`.

- [ ] **Step 3: Update `CLAUDE.md` output-formats + LLM-task sections**

In `CLAUDE.md`, under **## Decisions locked in**, replace the `**Output formats (v1):**` bullet (the one starting "a **web page** like HF Daily Papers … plus an **RSS/Atom feed**") with:

```
- **Output formats (v1):** a single-page **web app** (HF Daily Papers style) — a full-width,
  responsive **card grid** browsable by a **date strip** (latest selected by default), plus a
  separate **Search** tab (title/author text search + multi-select subfield-tag filter). Built as
  one `index.html` shell + a `data.json` payload rendered client-side. **RSS and the archive page
  were removed** (superseded by the date strip + search). A daily email digest is still deferred.
```

Then, under **## LLM task spec (DeepSeek — the only LLM call)**, replace the opening line:

```
The LLM has **one job**: classify a single candidate paper (already past the cheap prefilter).
No summarizing, ranking, or rewriting.
```

with:

```
The LLM has **two jobs** per candidate paper (already past the cheap prefilter): (1) classify it
in/out of scope and assign subfield tags, and (2) write a **two-sentence summary** — sentence one
states the specific problem the paper investigates, sentence two states its key method/innovation
(specific, using the paper's own terminology; the most important points of this paper, not
background). No ranking or rewriting beyond that summary.
```

Then update the **Output (JSON mode …)** example in that same section: change the field `"reason"` to `"summary"` and its comment to describe the two-sentence summary, e.g.:

```
  { "in_scope": true,
    "tags": ["operator-learning", "pde-foundation-models"],
    "summary": "Solving many PDE families with one model is hard. Introduces a neural operator pretrained across PDE families and fine-tunable to new ones." }
```

and change the following sentence `` `reason` = one sentence, reused as the site card blurb + debugging aid. `` to `` `summary` = two sentences, shown as the site card blurb. `` Also, in the BATCH MODE reference and the funnel/monitoring bullets, change any remaining mention of `reason` to `summary`.

- [ ] **Step 4: Update `README.md`**

In `README.md`, make these edits:
- In **## Why**, change "each with a one-line \"why it matters\"" to "each with a **two-sentence summary** (the problem it tackles + its key method)".
- In **## What you get**, replace the two bullets:
  - `- **One-line summaries** — skim the gist; click through only what grabs you.`
  - the `- **Subscribe by RSS** …` bullet (two lines)

  with:
  ```
  - **Two-sentence summaries** — the problem each paper tackles and its key method, at a glance.
  - **Browse by date** — a date strip jumps to any day; the latest day is shown by default.
  - **Search tab** — filter all papers by title, author, and subfield tags.
  ```
  And change `- **Instant search** — filter by title, author, or abstract as you type.` — remove it (now covered by the Search tab bullet above).

- [ ] **Step 5: Verify no stray RSS/reason references remain in docs/config**

Run:
```bash
grep -in "rss\|feed.xml\|RSS_COUNT" README.md CLAUDE.md config.py || echo "no rss references"
grep -in '"reason"\|one-line' README.md CLAUDE.md || echo "no reason/one-line references"
```
Expected: `no rss references`; `no reason/one-line references`. (If a benign mention remains in context, confirm it is intentional.)

- [ ] **Step 6: Commit**

```bash
git add config.py CLAUDE.md README.md
git commit -m "docs: update CLAUDE.md/README for SPA + summary; drop RSS_COUNT

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: Full integration verification

**Files:** none (verification only)

- [ ] **Step 1: Run the whole test suite**

Run: `pytest -q`
Expected: all tests pass (no references to `reason`, `feed.xml`, `archive.html`, or per-day pages remain in tests).

- [ ] **Step 2: Clean rebuild from real data**

Run:
```bash
python3 -c "import build; build.build(build.load_papers())"
git status --porcelain docs
```
Expected: `docs/index.html`, `docs/data.json`, and `docs/static/*` are the only build outputs; no `feed.xml`/`archive.html`/`day/` reappear.

- [ ] **Step 3: Confirm the GitHub Actions workflow still matches**

Read `.github/workflows/daily.yml`. It runs `python main.py` (which calls `build.build`) and then `git add docs data`. Confirm no step references `feed.xml`, `archive.html`, or `docs/day`. No change is expected; if any such reference exists, remove it.

Run:
```bash
grep -n "feed.xml\|archive.html\|docs/day" .github/workflows/daily.yml || echo "workflow clean"
```
Expected: `workflow clean`.

- [ ] **Step 4: Final manual smoke test (local server)**

Run:
```bash
python3 -m http.server 8000 --directory docs
```
Open `http://localhost:8000/` and confirm:
- Daily view loads the latest date by default; date strip scrolled to the right with latest active.
- Resizing the window reflows the card grid (many abreast when wide, 1–2 when narrow).
- Cards show: title (opens arXiv in new tab), two-sentence summary, tag pills, arXiv badge, authors (≤10 then "+N"), working Abstract toggle. No reason text, no upvotes.
- Search tab: typing filters by title/author; tag pills multi-select (OR); "All" clears; results show dates.
- Only two tabs (Daily, Search); no Today/Archive/RSS anywhere; no tagline sentence on the page.

- [ ] **Step 5: Final commit if anything changed during verification**

```bash
git add -A
git commit -m "chore: rebuild site after UI redesign

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || echo "nothing to commit"
```

---

## Self-review notes (coverage map)

- Spec §3 SPA / data.json shape → Task 5 (build) + Task 4 (shell) + Task 7 (renderer).
- Spec §4 full-width grid, Plus Jakarta Sans, auto theme, removed filler → Task 6 (CSS) + Task 4 shell (no tagline on page).
- Spec §5.1 card (no preview/reason, authors ≤10 +N, abstract toggle) → Task 6 CSS + Task 7 `card()`.
- Spec §5.2 two tabs + hash routing → Task 4 shell + Task 7 `route()/wire()`.
- Spec §5.3 daily date strip (latest default, scrolled) → Task 7 `renderStrip()/showDaily()`.
- Spec §5.4 search (title/author text + multi-select OR tags, all dates) → Task 7 `runSearch()/renderPills()`.
- Spec §6 two-sentence summary (prompt + classify + data + card; no backfill, local rename) → Tasks 1, 2, 3, plus build fallback in Task 5.
- Spec §7 fonts/theme → Task 4 shell font link + Task 6 tokens.
- Spec §8 housekeeping (CLAUDE.md, README.md, config.py, tests, workflow) → Tasks 1/5 (tests), 9, 10.
- Spec §9 file-by-file → Tasks 4–9. Spec §10 edge cases → Task 7 (`!byDate[date]` fallback, accent fallback, authors "+N", `summary||reason||""` in Task 5, strip scroll).
