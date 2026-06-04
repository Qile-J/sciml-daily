# SciML Daily Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily, $0, unattended pipeline that scrapes new arXiv + OpenReview papers, classifies the SciML / AI-for-scientific-computing / AI-for-applied-math ones with Gemini Flash, and publishes a clean, inviting "morning read" website + RSS feed via GitHub Actions + Pages.

**Architecture:** Five small flat Python files. `scrape.py` fetches (arXiv API over a generous category set + OpenReview), dedups, and keyword-prefilters. `classify.py` batches the survivors through Gemini (the only LLM). `build.py` renders the static site + RSS with Jinja2. `main.py` orchestrates and persists state to two plain files — `data/seen.txt` (append-only IDs, for classify-once) and `data/papers.json` (the in-scope feed). `config.py` is the single source of truth. The site is built into `docs/` and served by GitHub Pages straight from that folder.

**Tech Stack:** Python 3.11, `requests` (arXiv API, OpenReview, Gemini), `google-genai` (Gemini, JSON mode), `jinja2`. Papers are plain dicts (JSON-native) — no database, no dataclasses. Deployed on GitHub Pages from `/docs`.

---

## Design notes (read once)

- **Single source of truth:** `config.py` holds categories, prefilter keywords, the tag taxonomy (slug → name + color), the model name, batch size, and the request cap. The LLM-facing tag *descriptions* live in the approved `prompts/classify.md`; the machine list lives in `config.TAGS`. Keep the slugs in sync (noted in `config.py`).
- **Plain dicts everywhere.** A paper is `{"id","source","title","abstract","categories","authors","url","published"}`; classification merges in `"in_scope","tags","reason"`; the feed adds `"added"` (the run date it surfaced). JSON in, JSON out — nothing to map.
- **State = two files.** `data/seen.txt` is every processed ID (one per line, append-only) so we classify once, ever. `data/papers.json` is the list of in-scope papers the site renders. Both are committed back each run; both are text and diff cleanly.
- **Testability.** Network and LLM calls are injected (`get=`, `fetch=`, `generate=`), so every test runs offline against fixtures.
- **Simplicity over flexibility.** No provider abstraction, no plugins, no ORM. One model, flat files, plain functions.

## File Structure

```
.
├── config.py                 single source of truth
├── scrape.py                 fetch (arXiv + OpenReview) + dedup + prefilter
├── classify.py               batched Gemini classification
├── build.py                  Jinja2 → static site + RSS
├── main.py                   orchestrate + persist (seen.txt, papers.json)
├── prompts/classify.md       (exists — approved prompt)
├── templates/
│   ├── page.html             index + per-day page (one template)
│   ├── archive.html          list of days
│   └── feed.xml              RSS
├── static/
│   ├── style.css             the "morning read" UI
│   └── app.js                tag filter + search + abstract toggles
├── data/                     seen.txt + papers.json (committed state)
├── docs/                     generated site (committed; Pages serves this)
├── tests/                    test_scrape / test_classify / test_build / test_main
├── requirements.txt
├── pytest.ini
├── .gitignore
├── README.md
└── .github/workflows/daily.yml
```

---

## Task 0: Scaffold + config

**Files:**
- Create: `requirements.txt`, `.gitignore`, `pytest.ini`, `config.py`, `data/.gitkeep`, `docs/.gitkeep`, `tests/__init__.py`

- [ ] **Step 1: `requirements.txt`**

```
requests==2.32.3
jinja2==3.1.4
google-genai==1.20.0
pytest==8.3.3
```

- [ ] **Step 2: `.gitignore`** (note: `data/` and `docs/` are committed on purpose — not ignored)

```
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
```

- [ ] **Step 3: `pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: `config.py`**

```python
"""Single source of truth. The TAGS slugs must match prompts/classify.md."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"                       # GitHub Pages serves from here
PROMPT = ROOT / "prompts" / "classify.md"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
SEEN_FILE = DATA / "seen.txt"
PAPERS_FILE = DATA / "papers.json"

# arXiv: generous but specific categories (measured live 2026-06: ~400–600 papers/day). Edit freely.
ARXIV_CATEGORIES = [
    "cs.LG", "cs.NA", "cs.AI", "cs.CL", "cs.CE", "stat.ML",
    "math.NA", "math.OC", "math.DS", "math.AP", "math.PR", "math-ph",
    "physics.comp-ph", "physics.flu-dyn", "eess.SY",
]
LOOKBACK_DAYS = 2                          # re-scan a few days; seen-filter dedups

# OpenReview (set OPENREVIEW = False to skip)
OPENREVIEW = True
OPENREVIEW_VENUES = ["ICLR.cc/2026/Conference", "NeurIPS.cc/2025/Conference"]

# Gemini — the only model. Bump this one line for new versions.
GEMINI_MODEL = "gemini-3.5-flash"
BATCH_SIZE = 20                            # papers per request
MAX_REQUESTS = 1200                        # daily backstop under the ~1,500 free tier
REQUEST_DELAY = 6.0                        # seconds between calls (~10 RPM)

# Subfield tags: slug -> (display name, pill color). Keep slugs in sync with prompts/classify.md.
TAGS = {
    "operator-learning":                    ("Operator Learning",         "#6366f1"),
    "pde-foundation-models":                ("PDE Foundation Models",     "#0ea5e9"),
    "physics-informed-ml":                  ("Physics-Informed ML",       "#14b8a6"),
    "generative-simulation":                ("Generative Simulation",     "#ec4899"),
    "differentiable-simulation":            ("Differentiable Simulation", "#f59e0b"),
    "ml-numerical-methods":                 ("ML Numerical Methods",      "#8b5cf6"),
    "equation-discovery-dynamical-systems": ("Equation Discovery",        "#10b981"),
    "llm-agents-for-sci-computing":         ("LLM Agents for SciComp",    "#ef4444"),
    "uq-inverse-problems":                  ("UQ & Inverse Problems",     "#3b82f6"),
    "foundations":                          ("Foundations",               "#64748b"),
    "mathematical-analysis-of-llm":         ("Math Analysis of LLMs",     "#a855f7"),
}

# Prefilter keywords (lowercased substring match; recall-first, the LLM enforces precision).
KEYWORDS = [
    "neural operator", "fourier neural operator", "deeponet", "operator learning",
    "physics-informed", "physics informed", "pinn", "pino", "deep energy method",
    "pde", "partial differential equation", "differential equation",
    "surrogate model", "reduced-order", "reduced order model", "emulator",
    "differentiable simulation", "differentiable physics", "differentiable solver",
    "scientific machine learning", "scientific computing",
    "numerical method", "numerical analysis", "finite element", "finite difference",
    "spectral method", "preconditioner", "linear solver",
    "symbolic regression", "sindy", "equation discovery", "koopman", "neural ode",
    "dynamical system", "data assimilation", "inverse problem",
    "uncertainty quantification", "gaussian process",
    "diffusion model", "generative model", "turbulence", "navier-stokes",
    "foundation model", "large language model", " llm", "transformer", "attention",
    "autoformalization", "theorem proving", "mean-field", "mean field",
    "markov chain", "generalization bound", "in-context learning", "expressivity",
    "approximation theory", "convergence rate", "neural network",
]

SITE_TITLE = "SciML Daily"
SITE_TAGLINE = "New papers in Scientific ML, AI for Scientific Computing & Applied Math — every morning."
SITE_URL = "https://USERNAME.github.io/REPO"   # set to your Pages URL (used in links + RSS)
RSS_COUNT = 60
```

- [ ] **Step 5: empty marker files** — `data/.gitkeep`, `docs/.gitkeep`, `tests/__init__.py` (all empty).

- [ ] **Step 6: Verify**

Run: `pip install -r requirements.txt && python -c "import config; print(config.GEMINI_MODEL, len(config.TAGS))"`
Expected: prints `gemini-3.5-flash 11`

- [ ] **Step 7: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold and config"
```

---

## Task 1: `scrape.py` — fetch + dedup + prefilter

**Files:**
- Create: `scrape.py`
- Test: `tests/test_scrape.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scrape.py
import scrape

ARXIV_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <id>http://arxiv.org/abs/2406.01234v1</id>
  <title>A Neural Operator</title>
  <summary>  We learn operators for PDEs.  </summary>
  <published>2026-06-03T00:00:00Z</published>
  <author><name>Jane Doe</name></author>
  <category term="cs.LG"/><category term="math.NA"/>
 </entry>
</feed>"""
EMPTY = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'

def test_parse_arxiv():
    p = scrape.parse_arxiv(ARXIV_XML)[0]
    assert p["id"] == "arxiv:2406.01234"
    assert p["source"] == "arXiv"
    assert p["title"] == "A Neural Operator"
    assert p["abstract"] == "We learn operators for PDEs."
    assert p["categories"] == ["cs.LG", "math.NA"]
    assert p["authors"] == ["Jane Doe"]
    assert p["url"] == "https://arxiv.org/abs/2406.01234"
    assert p["published"] == "2026-06-03"

def test_fetch_arxiv_paginates_and_windows():
    pages = [ARXIV_XML, EMPTY]
    starts = []
    def get(start):
        starts.append(start)
        return pages[min(len(starts) - 1, 1)]
    out = scrape.fetch_arxiv("2026-06-01", get=get, sleep=lambda s: None)
    assert [p["id"] for p in out] == ["arxiv:2406.01234"]
    assert starts == [0, 100]

def test_fetch_arxiv_excludes_before_window():
    def get(start):
        return ARXIV_XML if start == 0 else ""
    out = scrape.fetch_arxiv("2026-06-05", get=get, sleep=lambda s: None)
    assert out == []

OR_PAYLOAD = {"notes": [{"id": "abc", "cdate": 1717372800000, "content": {
    "title": {"value": "Operator Learning"},
    "abstract": {"value": "Neural operators."},
    "authors": {"value": ["A One", "B Two"]}}}]}

def test_parse_openreview():
    p = scrape.parse_openreview(OR_PAYLOAD, "ICLR.cc/2026/Conference")[0]
    assert p["id"] == "openreview:abc"
    assert p["source"] == "OpenReview"
    assert p["title"] == "Operator Learning"
    assert p["authors"] == ["A One", "B Two"]
    assert p["url"] == "https://openreview.net/forum?id=abc"
    assert p["categories"] == ["ICLR.cc/2026/Conference"]

def test_fetch_openreview_is_defensive():
    def boom(venue):
        raise RuntimeError("down")
    assert scrape.fetch_openreview(["X"], fetch=boom) == []

def test_is_candidate():
    assert scrape.is_candidate({"title": "Neural operator", "abstract": "for PDEs"}) is True
    assert scrape.is_candidate({"title": "Cake recipe", "abstract": "baking"}) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scrape.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrape'`

- [ ] **Step 3: Write the implementation**

```python
# scrape.py
import time
import urllib.parse
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import requests
import config

ATOM = "{http://www.w3.org/2005/Atom}"
EMPTY_FEED = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'

def _clean(s):
    return " ".join(s.split()) if s else ""

# ---------- arXiv ----------
def parse_arxiv(xml_text):
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall(f"{ATOM}entry"):
        aid = (e.findtext(f"{ATOM}id") or "").rsplit("/abs/", 1)[-1].split("v")[0]
        out.append({
            "id": f"arxiv:{aid}", "source": "arXiv",
            "title": _clean(e.findtext(f"{ATOM}title")),
            "abstract": _clean(e.findtext(f"{ATOM}summary")),
            "categories": [c.get("term") for c in e.findall(f"{ATOM}category") if c.get("term")],
            "authors": [a for a in (_clean(x.findtext(f"{ATOM}name"))
                                    for x in e.findall(f"{ATOM}author")) if a],
            "url": f"https://arxiv.org/abs/{aid}",
            "published": (e.findtext(f"{ATOM}published") or "")[:10],
        })
    return out

def _arxiv_get(start):
    q = urllib.parse.urlencode({
        "search_query": "(" + " OR ".join(f"cat:{c}" for c in config.ARXIV_CATEGORIES) + ")",
        "start": start, "max_results": 100,
        "sortBy": "submittedDate", "sortOrder": "descending"})
    r = requests.get(f"http://export.arxiv.org/api/query?{q}",
                     headers={"User-Agent": "sciml-daily/1.0"}, timeout=60)
    return r.text if r.ok else ""

def fetch_arxiv(since, get=None, sleep=time.sleep):
    """Newest-first pages until we cross below `since` (YYYY-MM-DD)."""
    get = get or _arxiv_get
    papers, start = [], 0
    while start < 2000:
        batch = parse_arxiv(get(start) or EMPTY_FEED)
        if not batch:
            break
        papers += batch
        if batch[-1]["published"] < since:
            break
        start += 100
        sleep(3)                       # arXiv API politeness
    return [p for p in papers if p["published"] >= since]

# ---------- OpenReview ----------
def _val(content, key, default=""):
    f = content.get(key)
    return f.get("value", default) if isinstance(f, dict) else (f if f is not None else default)

def _ms_day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d") if ms else ""

def parse_openreview(payload, venue):
    out = []
    for n in payload.get("notes", []):
        c = n.get("content", {})
        title, abstract = _val(c, "title"), _val(c, "abstract")
        if not title or not abstract:
            continue
        out.append({
            "id": f"openreview:{n['id']}", "source": "OpenReview",
            "title": str(title).strip(), "abstract": str(abstract).strip(),
            "categories": [venue], "authors": list(_val(c, "authors", []) or []),
            "url": f"https://openreview.net/forum?id={n['id']}",
            "published": _ms_day(n.get("cdate")),
        })
    return out

def _or_fetch(venue):
    r = requests.get("https://api2.openreview.net/notes",
                     params={"content.venueid": venue, "limit": 1000}, timeout=60)
    r.raise_for_status()
    return r.json()

def fetch_openreview(venues, fetch=None):
    fetch = fetch or _or_fetch
    out = []
    for v in venues:
        try:
            out += parse_openreview(fetch(v), v)
        except Exception as e:            # one bad venue must not kill the run
            print(f"[openreview] skip {v}: {e}")
    return out

# ---------- combine + prefilter ----------
_KW = [k.lower() for k in config.KEYWORDS]

def is_candidate(p):
    text = (p["title"] + " " + p["abstract"]).lower()
    return any(k in text for k in _KW)

def fetch_all(since):
    """Deduped list of all fetched papers in the window (arXiv + OpenReview)."""
    papers = fetch_arxiv(since)
    if config.OPENREVIEW:
        papers += fetch_openreview(config.OPENREVIEW_VENUES)
    seen, out = set(), []
    for p in papers:
        if p["id"] not in seen:
            seen.add(p["id"])
            out.append(p)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scrape.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add scrape.py tests/test_scrape.py
git commit -m "feat: arXiv + OpenReview fetch with dedup and keyword prefilter"
```

---

## Task 2: `classify.py` — batched Gemini

**Files:**
- Create: `classify.py`
- Test: `tests/test_classify.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_classify.py
import classify, config

def papers(n):
    return [{"id": f"arxiv:{i}", "title": f"T{i}", "abstract": f"A{i}",
             "categories": ["cs.LG"]} for i in range(n)]

def test_load_instruction():
    s = classify.load_instruction()
    assert "IN scope" in s and "operator-learning" in s and "USER MESSAGE" not in s

def test_build_message_numbers_papers():
    m = classify.build_message(papers(2))
    assert "[1]" in m and "[2]" in m and "T0" in m and "A1" in m

def test_classify_validates_and_drops_unknown_tags():
    def gen(instr, msg):
        return ('[{"id":1,"in_scope":true,"tags":["operator-learning","nope"],"reason":"r"},'
                '{"id":2,"in_scope":false,"tags":[],"reason":"out"}]')
    out = classify.classify(papers(2), gen, instruction="x", sleep=lambda s: None)
    assert out[0]["in_scope"] is True and out[0]["tags"] == ["operator-learning"]
    assert out[1]["in_scope"] is False and out[1]["tags"] == []

def test_classify_respects_cap(monkeypatch):
    monkeypatch.setattr(config, "BATCH_SIZE", 1)
    monkeypatch.setattr(config, "MAX_REQUESTS", 2)
    calls = {"n": 0}
    def gen(instr, msg):
        calls["n"] += 1
        return '[{"id":1,"in_scope":true,"tags":[],"reason":"r"}]'
    out = classify.classify(papers(5), gen, instruction="x", sleep=lambda s: None)
    assert calls["n"] == 2 and len(out) == 2

def test_classify_survives_bad_json():
    out = classify.classify(papers(1), lambda i, m: "boom", instruction="x", sleep=lambda s: None)
    assert out == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_classify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'classify'`

- [ ] **Step 3: Write the implementation**

```python
# classify.py
import json
import os
import time
import config

def load_instruction():
    """The fixed system-instruction block from prompts/classify.md."""
    t = config.PROMPT.read_text(encoding="utf-8")
    block = t[t.index("## SYSTEM INSTRUCTION"):t.index("## USER MESSAGE")]
    return block.split("\n", 1)[1].strip()           # drop the header line

def build_message(batch):
    lines = ['Classify each paper. Return a JSON array, one object per paper, '
             'in the same order, each with its "id".', ""]
    for i, p in enumerate(batch, 1):
        lines += [f"[{i}]", f"Title: {p['title']}", f"Abstract: {p['abstract']}",
                  f"Categories: {', '.join(p['categories'])}", ""]
    return "\n".join(lines)

def _apply(item, p):
    valid = set(config.TAGS)
    in_scope = bool(item.get("in_scope"))
    tags = [t for t in (item.get("tags") or []) if t in valid] if in_scope else []
    return {**p, "in_scope": in_scope, "tags": tags, "reason": str(item.get("reason", ""))[:300]}

def classify(papers, generate, instruction=None, sleep=time.sleep):
    """Return classified papers (in + out) for as many as the request cap allows.
    Papers we never reach simply aren't returned — they stay unseen and retry next run."""
    instruction = instruction or load_instruction()
    done, used = [], 0
    for i in range(0, len(papers), config.BATCH_SIZE):
        if used >= config.MAX_REQUESTS:
            print(f"[classify] request cap hit; deferring {len(papers) - i} papers")
            break
        batch = papers[i:i + config.BATCH_SIZE]
        try:
            data = json.loads(generate(instruction, build_message(batch)))
            by_id = {int(x["id"]): x for x in data if "id" in x}
        except Exception as e:                        # bad JSON / API error: skip, retry next run
            print(f"[classify] batch failed: {e}")
            used += 1
            sleep(config.REQUEST_DELAY)
            continue
        for j, p in enumerate(batch, 1):
            if j in by_id:
                done.append(_apply(by_id[j], p))
        used += 1
        sleep(config.REQUEST_DELAY)
    return done

def gemini_generate(instruction, message):
    """Real Gemini call (not exercised by unit tests)."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=config.GEMINI_MODEL, contents=message,
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            response_mime_type="application/json", temperature=0.0))
    return resp.text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_classify.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add classify.py tests/test_classify.py
git commit -m "feat: batched Gemini classifier with cap and tag validation"
```

---

## Task 3: `build.py` + UI (templates, CSS, JS)

**Files:**
- Create: `build.py`, `templates/page.html`, `templates/archive.html`, `templates/feed.xml`, `static/style.css`, `static/app.js`
- Test: `tests/test_build.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build.py
import build

PAPER = {"id": "arxiv:1", "source": "arXiv", "title": "Neural Operator X",
         "abstract": "We solve PDEs.", "authors": ["Jane Doe"],
         "url": "https://arxiv.org/abs/1", "tags": ["operator-learning"],
         "reason": "New operator method.", "added": "2026-06-03"}

def test_build_renders_everything(tmp_path):
    out = tmp_path / "docs"
    build.build([PAPER], out=out)
    idx = (out / "index.html").read_text()
    assert "Neural Operator X" in idx
    assert "New operator method." in idx          # the reason hook
    assert "Operator Learning" in idx             # tag display name
    assert "Tuesday, June 3, 2026" in idx         # pretty date
    assert (out / "day" / "2026-06-03.html").exists()
    assert (out / "archive.html").exists()
    assert "Neural Operator X" in (out / "feed.xml").read_text()
    assert (out / "static" / "style.css").exists()

def test_build_empty_still_writes_index(tmp_path):
    out = tmp_path / "docs"
    build.build([], out=out)
    assert (out / "index.html").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'build'`

- [ ] **Step 3: Write `build.py`**

```python
# build.py
import json
import shutil
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
import config

def load_papers():
    if config.PAPERS_FILE.exists():
        return json.loads(config.PAPERS_FILE.read_text(encoding="utf-8"))
    return []

def _group_by_day(papers):
    days = {}
    for p in papers:
        days.setdefault(p["added"], []).append(p)
    return dict(sorted(days.items(), reverse=True))   # newest day first

def build(papers, out=None):
    out = out or config.DOCS
    env = Environment(loader=FileSystemLoader(str(config.TEMPLATES)),
                      autoescape=select_autoescape(["html", "xml"]))
    env.filters["pretty"] = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%A, %B %-d, %Y")

    days = _group_by_day(papers)
    day_list = list(days.keys())
    tags = {slug: {"name": n, "color": c} for slug, (n, c) in config.TAGS.items()}
    ctx = dict(site_title=config.SITE_TITLE, tagline=config.SITE_TAGLINE,
               url=config.SITE_URL.rstrip("/"), tags=tags, days=day_list)

    (out / "day").mkdir(parents=True, exist_ok=True)
    page = env.get_template("page.html")
    for d, ps in days.items():
        (out / "day" / f"{d}.html").write_text(page.render(**ctx, day=d, papers=ps), encoding="utf-8")

    latest = day_list[0] if day_list else None
    (out / "index.html").write_text(
        page.render(**ctx, day=latest, papers=days.get(latest, [])), encoding="utf-8")

    (out / "archive.html").write_text(
        env.get_template("archive.html").render(**ctx, counts=[(d, len(days[d])) for d in day_list]),
        encoding="utf-8")

    recent = sorted(papers, key=lambda p: p["added"], reverse=True)[:config.RSS_COUNT]
    (out / "feed.xml").write_text(
        env.get_template("feed.xml").render(**ctx, papers=recent), encoding="utf-8")

    dst = out / "static"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(config.STATIC, dst)
```

- [ ] **Step 4: Write `templates/page.html`** (index + per-day, one template)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ site_title }}{% if day %} · {{ day | pretty }}{% endif %}</title>
<meta name="description" content="{{ tagline }}">
<link rel="alternate" type="application/rss+xml" title="{{ site_title }}" href="{{ url }}/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{ url }}/static/style.css">
</head>
<body>
<header class="topbar">
  <a class="brand" href="{{ url }}/">{{ site_title }}</a>
  <nav>
    <a href="{{ url }}/">Today</a>
    <a href="{{ url }}/archive.html">Archive</a>
    <a href="{{ url }}/feed.xml">RSS</a>
  </nav>
</header>

<main>
  <section class="masthead">
    <p class="kicker">{{ tagline }}</p>
    <h1>{% if day %}{{ day | pretty }}{% else %}No papers yet{% endif %}</h1>
    <p class="count"><span id="visible-count">{{ papers|length }}</span> papers</p>
  </section>

  {% if papers %}
  <div class="controls">
    <input id="search" type="search" placeholder="Search titles, abstracts, authors…" autocomplete="off">
    <div class="pills" id="pills">
      <button class="pill active" data-tag="">All</button>
      {% for slug, t in tags.items() %}
      <button class="pill" data-tag="{{ slug }}" style="--c:{{ t.color }}">{{ t.name }}</button>
      {% endfor %}
    </div>
  </div>

  <ul class="papers" id="papers">
    {% for p in papers %}
    <li class="paper" data-tags="{{ p.tags|join(' ') }}"
        data-text="{{ (p.title ~ ' ' ~ p.abstract ~ ' ' ~ p.authors|join(' '))|lower }}"
        style="--accent:{{ tags[p.tags[0]].color if p.tags else '#cbd5e1' }}">
      <h2><a href="{{ p.url }}" target="_blank" rel="noopener">{{ p.title }}</a></h2>
      <p class="reason">{{ p.reason }}</p>
      {% if p.tags %}
      <div class="tags">
        {% for tg in p.tags %}<span class="tag" style="--c:{{ tags[tg].color }}">{{ tags[tg].name }}</span>{% endfor %}
      </div>
      {% endif %}
      <div class="meta">
        <span class="src">{{ p.source }}</span>
        <span class="authors">{{ p.authors[:4]|join(', ') }}{% if p.authors|length > 4 %} +{{ p.authors|length - 4 }}{% endif %}</span>
        <button class="abstract-toggle" aria-expanded="false">Abstract</button>
      </div>
      <p class="abstract" hidden>{{ p.abstract }}</p>
    </li>
    {% endfor %}
  </ul>
  <p class="empty" id="empty" hidden>No papers match.</p>
  {% else %}
  <p class="empty">Nothing yet — the next morning run will fill this in.</p>
  {% endif %}
</main>

<footer><p>{{ site_title }} — {{ tagline }}</p></footer>
<script src="{{ url }}/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 5: Write `templates/archive.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archive · {{ site_title }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{ url }}/static/style.css">
</head>
<body>
<header class="topbar">
  <a class="brand" href="{{ url }}/">{{ site_title }}</a>
  <nav>
    <a href="{{ url }}/">Today</a>
    <a href="{{ url }}/archive.html">Archive</a>
    <a href="{{ url }}/feed.xml">RSS</a>
  </nav>
</header>
<main>
  <section class="masthead"><h1>Archive</h1><p class="count">{{ counts|length }} days</p></section>
  <ul class="archive">
    {% for d, n in counts %}
    <li><a href="{{ url }}/day/{{ d }}.html">{{ d | pretty }}</a><span>{{ n }} papers</span></li>
    {% else %}
    <li class="empty">No days yet.</li>
    {% endfor %}
  </ul>
</main>
<footer><p>{{ site_title }}</p></footer>
</body>
</html>
```

- [ ] **Step 6: Write `templates/feed.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{{ site_title }}</title>
    <link>{{ url }}/</link>
    <description>{{ tagline }}</description>
    {% for p in papers %}
    <item>
      <title>{{ p.title }}</title>
      <link>{{ p.url }}</link>
      <guid isPermaLink="false">{{ p.id }}</guid>
      <description>{{ p.reason }} (tags: {{ p.tags|join(', ') }})</description>
    </item>
    {% endfor %}
  </channel>
</rss>
```

- [ ] **Step 7: Write `static/style.css`** (the "morning read" UI)

```css
:root{
  --bg:#fcfbf9; --surface:#ffffff; --ink:#1b1b1f; --muted:#6b6f76;
  --line:#ece9e3; --accent:#4f46e5;
  --shadow:0 1px 2px rgba(20,20,30,.04),0 8px 24px rgba(20,20,30,.05);
  --radius:16px;
}
@media (prefers-color-scheme:dark){
  :root{--bg:#0f1115;--surface:#171a20;--ink:#e9eaee;--muted:#9aa0ab;
    --line:#262a33;--accent:#8b8cf0;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);}
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:inherit}

.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;
  padding:14px 22px;background:color-mix(in srgb,var(--bg) 85%,transparent);
  backdrop-filter:saturate(140%) blur(10px);border-bottom:1px solid var(--line)}
.brand{font-family:Newsreader,serif;font-weight:600;font-size:20px;letter-spacing:-.01em;text-decoration:none}
.topbar nav a{margin-left:20px;color:var(--muted);text-decoration:none;font-size:14px;font-weight:500}
.topbar nav a:hover{color:var(--accent)}

main{max-width:740px;margin:0 auto;padding:0 22px 80px}
.masthead{padding:54px 0 26px;border-bottom:1px solid var(--line);margin-bottom:22px}
.kicker{margin:0 0 14px;color:var(--muted);font-size:14px;font-weight:500}
.masthead h1{font-family:Newsreader,serif;font-weight:600;font-size:clamp(30px,5vw,44px);
  line-height:1.1;letter-spacing:-.02em;margin:0}
.count{margin:12px 0 0;color:var(--muted);font-size:15px}

.controls{position:sticky;top:53px;z-index:10;background:var(--bg);padding:14px 0 4px;margin-bottom:8px}
#search{width:100%;padding:13px 16px;border:1px solid var(--line);border-radius:12px;
  background:var(--surface);color:var(--ink);font:inherit;font-size:15px;outline:none;
  transition:border-color .15s,box-shadow .15s}
#search:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 20%,transparent)}
.pills{display:flex;gap:8px;overflow-x:auto;padding:12px 0 2px;scrollbar-width:none}
.pills::-webkit-scrollbar{display:none}
.pill{flex:0 0 auto;border:1px solid var(--line);background:var(--surface);color:var(--muted);
  padding:7px 14px;border-radius:999px;font:inherit;font-size:13px;font-weight:500;cursor:pointer;
  white-space:nowrap;transition:color .15s,background .15s,border-color .15s}
.pill:hover{color:var(--ink);border-color:color-mix(in srgb,var(--c,var(--accent)) 50%,var(--line))}
.pill.active{color:#fff;background:var(--c,var(--accent));border-color:var(--c,var(--accent))}
.pill .n{opacity:.6;margin-left:6px}

.papers{list-style:none;margin:18px 0 0;padding:0;display:flex;flex-direction:column;gap:14px}
.paper{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px 24px 20px;box-shadow:var(--shadow);overflow:hidden;
  transition:transform .15s,box-shadow .15s}
.paper::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--accent)}
.paper:hover{transform:translateY(-2px);box-shadow:0 2px 4px rgba(20,20,30,.05),0 14px 36px rgba(20,20,30,.09)}
.paper h2{font-family:Newsreader,serif;font-weight:600;font-size:21px;line-height:1.3;
  letter-spacing:-.01em;margin:0 0 8px}
.paper h2 a{text-decoration:none}
.paper h2 a:hover{color:var(--accent)}
.reason{margin:0 0 14px;font-size:15.5px}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.tag{font-size:12px;font-weight:500;padding:3px 10px;border-radius:999px;
  color:var(--c);background:color-mix(in srgb,var(--c) 12%,transparent)}
.meta{display:flex;align-items:center;gap:12px;font-size:13px;color:var(--muted);flex-wrap:wrap}
.src{font-weight:600;letter-spacing:.02em;font-size:11px;text-transform:uppercase;
  padding:2px 8px;border-radius:6px;background:color-mix(in srgb,var(--muted) 14%,transparent)}
.authors{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.abstract-toggle{border:none;background:none;color:var(--accent);font:inherit;font-size:13px;
  font-weight:500;cursor:pointer;padding:0}
.abstract{margin:14px 0 0;padding-top:14px;border-top:1px solid var(--line);
  color:var(--muted);font-size:14.5px}
.empty{color:var(--muted);text-align:center;padding:50px 0}

.archive{list-style:none;padding:0;margin:0}
.archive li{display:flex;justify-content:space-between;align-items:baseline;
  padding:16px 4px;border-bottom:1px solid var(--line)}
.archive a{font-family:Newsreader,serif;font-size:18px;text-decoration:none}
.archive a:hover{color:var(--accent)}
.archive span{color:var(--muted);font-size:14px}
footer{max-width:740px;margin:0 auto;padding:30px 22px;color:var(--muted);font-size:13px;
  text-align:center;border-top:1px solid var(--line)}
```

- [ ] **Step 8: Write `static/app.js`** (tag filter + search + per-tag counts + abstract toggles)

```javascript
(function () {
  var papers = [].slice.call(document.querySelectorAll(".paper"));
  var pills = [].slice.call(document.querySelectorAll(".pill"));
  var search = document.getElementById("search");
  var counter = document.getElementById("visible-count");
  var empty = document.getElementById("empty");
  var activeTag = "";

  // per-tag counts on the pills; hide tags absent today
  var counts = {};
  papers.forEach(function (el) {
    (el.dataset.tags || "").split(" ").filter(Boolean).forEach(function (t) {
      counts[t] = (counts[t] || 0) + 1;
    });
  });
  pills.forEach(function (pill) {
    var t = pill.dataset.tag;
    var n = t ? counts[t] : papers.length;
    if (n) {
      var s = document.createElement("span");
      s.className = "n"; s.textContent = n; pill.appendChild(s);
    } else if (t) {
      pill.style.display = "none";
    }
  });

  function apply() {
    var q = (search && search.value || "").trim().toLowerCase();
    var shown = 0;
    papers.forEach(function (el) {
      var okTag = !activeTag || (el.dataset.tags || "").split(" ").indexOf(activeTag) !== -1;
      var okText = !q || (el.dataset.text || "").indexOf(q) !== -1;
      var vis = okTag && okText;
      el.style.display = vis ? "" : "none";
      if (vis) shown++;
    });
    if (counter) counter.textContent = shown;
    if (empty) empty.hidden = shown !== 0;
  }

  pills.forEach(function (pill) {
    pill.addEventListener("click", function () {
      activeTag = pill.dataset.tag;
      pills.forEach(function (p) { p.classList.remove("active"); });
      pill.classList.add("active");
      apply();
    });
  });
  if (search) search.addEventListener("input", apply);

  document.querySelectorAll(".abstract-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var ab = btn.closest(".paper").querySelector(".abstract");
      var open = !ab.hidden;
      ab.hidden = open;
      btn.setAttribute("aria-expanded", String(!open));
      btn.textContent = open ? "Abstract" : "Hide abstract";
    });
  });
})();
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `pytest tests/test_build.py -v`
Expected: PASS (2 passed)

- [ ] **Step 10: Eyeball the UI** — render a sample and open it.

Run: `python -c "import build; build.build([{'id':'arxiv:1','source':'arXiv','title':'Geometry-Aware Fourier Neural Operator','abstract':'We solve parametric PDEs.','authors':['Jane Doe','J. Smith'],'url':'https://arxiv.org/abs/1','tags':['operator-learning','pde-foundation-models'],'reason':'A new neural-operator architecture for parametric PDEs.','added':'2026-06-03'}])" && open docs/index.html`
Expected: a clean card with serif title, reason blurb, two colored tag pills, working filter/search.

- [ ] **Step 11: Commit**

```bash
git add build.py templates static tests/test_build.py
git commit -m "feat: static site + RSS with a modern morning-read UI"
```

---

## Task 4: `main.py` — orchestrate + persist

**Files:**
- Create: `main.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_main.py
import json
import main, config, scrape

def _wire(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEEN_FILE", tmp_path / "seen.txt")
    monkeypatch.setattr(config, "PAPERS_FILE", tmp_path / "papers.json")
    monkeypatch.setattr(config, "DOCS", tmp_path / "docs")

def test_run_end_to_end_offline(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch)
    fetched = [
        {"id": "arxiv:1", "source": "arXiv", "title": "Neural operator", "abstract": "pde surrogate",
         "categories": ["cs.LG"], "authors": ["X"], "url": "u", "published": "2026-06-03"},
        {"id": "arxiv:2", "source": "arXiv", "title": "cooking", "abstract": "cakes",
         "categories": ["cs.LG"], "authors": ["Y"], "url": "u", "published": "2026-06-03"},
    ]
    monkeypatch.setattr(scrape, "fetch_all", lambda since: fetched)
    def gen(instr, msg):
        return '[{"id":1,"in_scope":true,"tags":["operator-learning"],"reason":"r"}]'
    main.run(today="2026-06-04", generate=gen)

    papers = json.loads((tmp_path / "papers.json").read_text())
    assert [p["id"] for p in papers] == ["arxiv:1"]           # candidate + in-scope only
    assert papers[0]["added"] == "2026-06-04"
    assert (tmp_path / "docs" / "index.html").read_text().count("Neural operator") >= 1
    seen = (tmp_path / "seen.txt").read_text().split()
    assert "arxiv:1" in seen and "arxiv:2" in seen            # both marked processed

def test_run_classifies_once(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch)
    fetched = [{"id": "arxiv:1", "source": "arXiv", "title": "Neural operator", "abstract": "pde",
                "categories": ["cs.LG"], "authors": ["X"], "url": "u", "published": "2026-06-03"}]
    monkeypatch.setattr(scrape, "fetch_all", lambda since: fetched)
    calls = {"n": 0}
    def gen(instr, msg):
        calls["n"] += 1
        return '[{"id":1,"in_scope":true,"tags":[],"reason":"r"}]'
    main.run(today="2026-06-04", generate=gen)
    main.run(today="2026-06-05", generate=gen)
    assert calls["n"] == 1                                    # never re-classified
    assert len(json.loads((tmp_path / "papers.json").read_text())) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Write the implementation**

```python
# main.py
import json
import os
from datetime import date, timedelta
import config, scrape, classify, build

def _load_env():
    """Read a local .env (KEY=VALUE) if present, so local runs find GEMINI_API_KEY. No-op in CI."""
    env = config.ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def _load_seen():
    return set(config.SEEN_FILE.read_text().split()) if config.SEEN_FILE.exists() else set()

def _append_seen(ids):
    config.SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.SEEN_FILE, "a") as f:
        for i in ids:
            f.write(i + "\n")

def run(today=None, generate=None):
    _load_env()
    today = today or date.today().isoformat()
    since = (date.fromisoformat(today) - timedelta(days=config.LOOKBACK_DAYS)).isoformat()
    generate = generate or classify.gemini_generate

    seen = _load_seen()
    new = [p for p in scrape.fetch_all(since) if p["id"] not in seen]
    candidates = [p for p in new if scrape.is_candidate(p)]
    non_candidates = [p["id"] for p in new if not scrape.is_candidate(p)]
    print(f"[main] new {len(new)}, candidates {len(candidates)}")

    classified = classify.classify(candidates, generate) if candidates else []
    in_scope = [{**p, "added": today} for p in classified if p["in_scope"]]
    print(f"[main] classified {len(classified)}, in-scope {len(in_scope)}")

    papers = build.load_papers() + in_scope
    config.PAPERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.PAPERS_FILE.write_text(json.dumps(papers, indent=1, ensure_ascii=False), encoding="utf-8")
    _append_seen(non_candidates + [p["id"] for p in classified])

    build.build(papers)
    print("[main] done")

if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_main.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: all PASS (15 tests).

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: orchestration with classify-once persistence"
```

---

## Task 5: GitHub Actions daily workflow

**Files:**
- Create: `.github/workflows/daily.yml`

One job: run the pipeline with the secret key, then commit `docs/` + `data/` back. GitHub Pages serves `/docs` directly — no deploy job needed.

- [ ] **Step 1: Write `.github/workflows/daily.yml`**

```yaml
name: daily
on:
  schedule:
    - cron: "0 11 * * *"     # 11:00 UTC daily; adjust to your morning
  workflow_dispatch:          # manual "Run workflow" button

permissions:
  contents: write             # commit docs/ + data/

concurrency:
  group: daily
  cancel-in-progress: false

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: Run pipeline
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python main.py
      - name: Commit site + state
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs data
          git commit -m "daily $(date -u +%F)" || echo "no changes"
          git push
```

- [ ] **Step 2: Validate YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/daily.yml')); print('ok')"`
Expected: prints `ok` (run `pip install pyyaml` first if needed).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/daily.yml
git commit -m "ci: daily cron that runs the pipeline and commits the site"
```

> **One-time GitHub setup (UI, not code):**
> 1. Push the repo to GitHub.
> 2. Settings → Secrets and variables → Actions → add `GEMINI_API_KEY`.
> 3. Settings → Pages → Source = "Deploy from a branch" → branch `main`, folder `/docs`.
> 4. Set `config.SITE_URL` to `https://<user>.github.io/<repo>` and commit.
> 5. Actions → run "daily" once via "Run workflow" to verify.

---

## Task 6: README + first run

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# SciML Daily

A daily, automatically-curated feed of new papers in **Scientific Machine Learning**,
**AI for Scientific Computing**, and **AI for Applied Mathematics** — harvested from arXiv
and OpenReview, classified by Gemini Flash, and published as a clean website + RSS feed.

Runs free, daily, unattended: GitHub Actions cron + GitHub Pages, Gemini free tier.

## How it works
`scrape` (arXiv + OpenReview) → dedup + keyword prefilter → `classify` (batched Gemini:
in/out + subfield tags) → store (`data/papers.json`, `data/seen.txt`) → `build` static site + RSS.
Each paper is classified once, ever. See `CLAUDE.md` for the full design and `prompts/classify.md`
for the classifier prompt.

## Run locally
\`\`\`bash
pip install -r requirements.txt
echo "GEMINI_API_KEY=your-free-key" > .env
python main.py
open docs/index.html
\`\`\`

## Configure
Everything lives in `config.py`: arXiv categories, prefilter keywords, the subfield tag
taxonomy (slug → name + color), the Gemini model, batch size, and OpenReview venues.

## Deploy
Push to GitHub, add `GEMINI_API_KEY` as an Actions secret, set Pages to serve `/docs` from
`main`, and set `SITE_URL` in `config.py`. The `daily` workflow does the rest.
```

- [ ] **Step 2: Full suite green**

Run: `pytest -v`
Expected: all PASS.

- [ ] **Step 3: Optional real run** (needs a Gemini key + network)

Run: `python main.py && open docs/index.html`
Expected: logs `new / candidates / classified / in-scope` counts; the site shows today's tagged papers.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README"
```

---

## Verification (end-to-end)

1. `pytest -v` — all 15 tests green; the `main` test proves scrape→prefilter→classify→store→build works offline and classifies each paper once.
2. **Local real run** with a key: `python main.py` produces `docs/index.html` with real, tagged papers and populates `data/`. Re-running adds nothing already seen.
3. **Budget:** logs show `candidates` ≈ 100–200 → ~5–10 Gemini requests (≪ the 1,500/day free tier).
4. **UI:** open `docs/index.html` — serif headlines, reason-blurb hooks, color-coded tag pills with live counts, instant search, collapsible abstracts, dark mode, 740px reading column.
5. **CI:** trigger "daily" manually; confirm it commits `docs/` + `data/` and Pages serves the site at `SITE_URL`.

## Notes for the implementer
- **DRY/YAGNI:** five flat files, plain dicts, one config. Don't add abstraction the spec didn't ask for.
- **Keep tags in sync:** `config.TAGS` slugs must match the allowed tags in `prompts/classify.md`.
- **OpenReview is the fragile source:** it's isolated and defensive; if a venue's schema differs, fix it in `scrape.py` only, or set `OPENREVIEW = False`.
- **`data/` and `docs/` are committed on purpose** — that's the state + the published site.
- **`%-d` in the pretty-date filter** is fine on the Linux CI runner and macOS; it would need `%#d` on Windows (not a target).

---

## Self-review

- **Spec coverage:** generous specific categories (`config.ARXIV_CATEGORIES`) ✓; arXiv + OpenReview + dedup (`scrape.py`) ✓; keyword prefilter ✓; batched Gemini, JSON, classify-once, request cap (`classify.py` + `seen.txt`) ✓; 11-tag taxonomy single source (`config.TAGS` ↔ prompt) ✓; static site archived by date + RSS + modern UI (`build.py`, templates, CSS/JS) ✓; GitHub Actions cron + Pages, $0, secret key (`daily.yml`) ✓; deferred items (ranking, email) absent ✓.
- **Placeholders:** none — every step has full code/commands.
- **Type consistency:** every module passes plain paper dicts with the keys defined in Design notes; `build`/templates read `tags`, `reason`, `added`, `authors`; `classify` writes exactly those. Function names (`fetch_all`, `is_candidate`, `classify`, `build`, `run`) are referenced consistently across tasks and tests.

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-04-sciml-paper-scraper.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — I execute tasks in this session with checkpoints for your review.

**Which approach?**
