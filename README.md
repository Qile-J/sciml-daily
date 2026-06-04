# SciML Daily

**Your morning read for Scientific Machine Learning.**

A daily, curated feed of new papers in **Scientific Machine Learning**, **AI for Scientific
Computing**, and **AI for Applied Mathematics** — the *methods*, not the whole "AI for Science"
firehose. Every morning it scans the latest arXiv and OpenReview papers, keeps only the ones that
matter to this space, and tags each by subfield so you can see what's new over coffee.

### 👉 Read it: **https://qile-j.github.io/sciml-daily**

## Why

The field moves fast and the firehose is loud. SciML Daily filters the day's new papers down to
just the ones about operator learning, physics-informed ML, PDE foundation models, differentiable
simulation, equation discovery, UQ & inverse problems, and the mathematical analysis of neural
networks — each with a one-line "why it matters" so you can decide in seconds.

## What you get

- **Fresh every morning** — the day's new papers, archived by date.
- **Tagged by subfield** — tap a tag to narrow the feed to exactly the topics you follow.
- **One-line summaries** — skim the gist; click through only what grabs you.
- **Subscribe by RSS** — drop the [feed](https://qile-j.github.io/sciml-daily/feed.xml) into your
  reader. No account, no email.
- **Instant search** — filter by title, author, or abstract as you type.

## Subfields covered

Operator learning · PDE foundation models · Physics-informed ML · Generative models for
simulation · Differentiable simulation · ML-accelerated numerical methods · Equation discovery &
dynamical systems · LLM agents for scientific computing · UQ & inverse problems · Mathematical
analysis of LLMs / neural nets · Foundations

## Run your own

Want a feed tuned to your own interests? Fork the repo, edit the categories, keywords, and tags in
`config.py`, add a free [Gemini API key](https://aistudio.google.com/apikey) as the GitHub Actions
secret `GEMINI_API_KEY`, and turn on GitHub Pages (`main` → `/docs`). The included workflow scrapes,
classifies, and republishes your site automatically every morning.
