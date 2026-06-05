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
networks — each with a **two-sentence summary** (the problem it tackles + its key method) so you
can decide in seconds.

## What you get

- **Fresh every morning** — the day's new papers, archived by date.
- **Tagged by subfield** — tap a tag to narrow the feed to exactly the topics you follow.
- **Two-sentence summaries** — the problem each paper tackles and its key method, at a glance.
- **Browse by date** — a date strip jumps to any day; the latest day is shown by default.
- **Search tab** — filter all papers by title, author, and subfield tags.

## Subfields covered

Operator learning · PDE foundation models · Physics-informed ML · Generative models for
simulation · Differentiable simulation · ML-accelerated numerical methods · Equation discovery &
dynamical systems · LLM agents for scientific computing · UQ & inverse problems · Mathematical
analysis of LLMs / neural nets · Foundations

## Run your own

Want a feed tuned to your own interests? Fork the repo, edit the categories, keywords, and tags in
`config.py`, add a [DeepSeek API key](https://platform.deepseek.com/api_keys) as the GitHub Actions
secret `DEEPSEEK_API_KEY`, and turn on GitHub Pages (`main` → `/docs`). The included workflow scrapes,
classifies, and republishes your site automatically every morning.
