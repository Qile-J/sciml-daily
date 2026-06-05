# SciML Daily

**A daily feed of new papers in Scientific Machine Learning, AI for Scientific Computing, and AI for Applied Math.**

&rarr; **[sciml-daily.github.io](https://qile-j.github.io/sciml-daily)**

---

Every morning, SciML Daily scans the latest arXiv and OpenReview submissions, keeps only the papers that matter to this space, and publishes them with two-sentence summaries and subfield tags. No noise from the broad "AI for Science" firehose. Just the methods.

## What it covers

| Tag | Topics |
|-----|--------|
| Operator learning | Neural operators (FNO, DeepONet), geometry-aware operators |
| PDE foundation models | Pretrained multi-PDE models (Poseidon, SPUS, P3) |
| Physics-informed ML | PINNs, PINO, deep energy methods, convergence theory |
| Generative models for simulation | Diffusion for PDEs, probabilistic surrogates |
| Differentiable simulation | Differentiable physics, hybrid physics-neural surrogates |
| ML-accelerated solvers | Learned solvers, reduced-order modeling |
| Equation discovery | SINDy, neural ODEs, Koopman/DMD, symbolic regression |
| LLMs for sci-computing | LLM agents for PDEs, autoformalization, solver codegen |
| Mathematical analysis of LLMs | Training dynamics, mean-field theory, expressivity bounds |
| UQ & inverse problems | Bayesian SciML, data assimilation, uncertainty quantification |

## How it works

```
arXiv + OpenReview  →  keyword prefilter  →  DeepSeek classify + summarize  →  GitHub Pages
```

- Runs daily on GitHub Actions (free, unattended)
- DeepSeek V4 Flash classifies each candidate — around 4-7 API calls per day, fractions of a cent
- Renders a static single-page app: browse by date, filter by tag, search by title or author

## Run your own

1. Fork this repo
2. Edit `config.py` — adjust categories, keywords, and subfield tags to your interests
3. Add your [DeepSeek API key](https://platform.deepseek.com/api_keys) as the secret `DEEPSEEK_API_KEY` in repo Settings → Secrets
4. Enable GitHub Pages: Settings → Pages → Source: `main` branch, `/docs` folder

The Actions workflow scrapes, classifies, and redeploys every morning automatically.

## Stack

- **Python** — fetch, prefilter, classify, render
- **DeepSeek V4 Flash** — the only paid dependency (~$0.01/month)
- **GitHub Actions** — daily cron runner (free for public repos)
- **GitHub Pages** — static hosting (free)
- **Vanilla JS + KaTeX** — client-side search, tag filter, math rendering
