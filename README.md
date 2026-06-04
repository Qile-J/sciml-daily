# SciML Daily

A daily, automatically-curated feed of new papers in **Scientific Machine Learning**,
**AI for Scientific Computing**, and **AI for Applied Mathematics** — harvested from arXiv
and OpenReview, classified by Gemini Flash, and published as a clean website + RSS feed.

Runs free, daily, and unattended: GitHub Actions cron + GitHub Pages, on the Gemini free tier.

## How it works

```
scrape (arXiv + OpenReview) → dedup + keyword prefilter → classify (batched Gemini:
in/out of scope + subfield tags) → store (data/papers.json, data/seen.txt)
→ build static site + RSS → deploy via GitHub Pages
```

Each paper is classified **once, ever** (keyed by ID in `data/seen.txt`), so daily runs only
spend LLM calls on genuinely new papers — a handful of batched requests per day, far under the
free-tier quota. The whole thing is five short Python files:

| File | Responsibility |
|------|----------------|
| `config.py`   | single source of truth — categories, keywords, tag taxonomy, model, site settings |
| `scrape.py`   | fetch arXiv + OpenReview, dedup, keyword prefilter |
| `classify.py` | the one and only LLM step — batched Gemini classification |
| `build.py`    | render the static site + RSS feed (Jinja2) |
| `main.py`     | orchestrate the pipeline and persist state |

See `CLAUDE.md` for the full design and `prompts/classify.md` for the classifier prompt.

## Run locally

```bash
pip install -r requirements.txt
echo "GEMINI_API_KEY=your-free-key" > .env      # never committed (.gitignore'd)
python main.py
open docs/index.html
```

Get a free key at <https://aistudio.google.com/apikey>. Tests run fully offline (no key, no network):

```bash
pytest
```

## Configure

Everything lives in `config.py`: the arXiv categories (`ARXIV_CATEGORIES`), prefilter keywords
(`KEYWORDS`), the subfield tag taxonomy (`TAGS`, slug → display name + color), the Gemini model
(`GEMINI_MODEL` — a one-line bump for new versions), batch size, and the OpenReview venues. The
tag slugs in `config.TAGS` must stay in sync with the allowed tags in `prompts/classify.md`.

## Deploy (one-time GitHub setup)

1. Push this repo to GitHub.
2. **Settings → Secrets and variables → Actions** → add a secret named `GEMINI_API_KEY`.
3. **Settings → Pages** → Source = "Deploy from a branch" → branch `main`, folder `/docs`.
4. Set `SITE_URL` in `config.py` to `https://<user>.github.io/<repo>` and commit.
5. **Actions → daily → Run workflow** to verify the first run.

After that, the `daily` workflow runs every morning: it scrapes, classifies new papers, rebuilds
the site into `docs/`, and commits the result — which GitHub Pages serves automatically.

## Cost

$0. The free Gemini tier (~1,500 requests/day) is never approached: classify-once + a
category/keyword prefilter + ~20-papers-per-request batching keeps a typical day at well under
1% of the quota. A hard daily request cap (`MAX_REQUESTS` in `config.py`) is a backstop; any
overflow simply waits for the next run.
