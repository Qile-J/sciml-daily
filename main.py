# main.py
import json
import os
from datetime import date, timedelta
import config, scrape, classify, build

def _load_env():
    """Read a local .env (KEY=VALUE) if present, so local runs find DEEPSEEK_API_KEY. No-op in CI."""
    env = config.ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def _log_run(record):
    """Append one run summary to data/stats.json — a maintainer-only log (not shown on the site)."""
    config.STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if config.STATS_FILE.exists():
        try:
            history = json.loads(config.STATS_FILE.read_text())
        except Exception:
            history = []
    history.append(record)
    config.STATS_FILE.write_text(json.dumps(history[-180:], indent=1), encoding="utf-8")

def run(today=None, generate=None, balance=None):
    _load_env()
    today = today or date.today().isoformat()
    generate = generate or classify.deepseek_generate
    balance = balance or classify.deepseek_balance

    bal_start = balance()
    since = (date.fromisoformat(today) - timedelta(days=config.FETCH_WINDOW_DAYS)).isoformat()
    existing = build.load_papers()                       # papers.json is the single store
    have = {p["id"] for p in existing}
    fetched = scrape.fetch_all(since)                     # last couple days, to absorb arXiv lag
    new = [p for p in fetched if p["id"] not in have]     # skip anything already in the feed
    candidates = [p for p in new if scrape.is_candidate(p)]
    print(f"[main] fetched {len(fetched)} · new {len(new)} · candidates {len(candidates)}")

    classified, used = classify.classify(candidates, generate) if candidates else ([], 0)
    in_scope = [{**p, "added": today} for p in classified if p["in_scope"]]
    deferred = len(candidates) - len(classified)

    papers = existing + in_scope
    config.PAPERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.PAPERS_FILE.write_text(json.dumps(papers, indent=1, ensure_ascii=False), encoding="utf-8")
    build.build(papers)

    bal_end = balance()
    _log_run({"date": today, "fetched": len(fetched), "new": len(new),
              "candidates": len(candidates), "classified": len(classified),
              "in_scope": len(in_scope), "deferred": deferred, "requests": used,
              "balance_before": bal_start, "balance_after": bal_end, "total_papers": len(papers)})

    print("[main] ───── run summary ─────")
    print(f"[main] candidates {len(candidates)} · classified {len(classified)} · "
          f"in-scope {len(in_scope)} · deferred {deferred}")
    print(f"[main] DeepSeek requests this run: {used}")
    print(f"[main] balance: {bal_start} -> {bal_end}")
    print(f"[main] site now lists {len(papers)} papers. done.")

if __name__ == "__main__":
    run()
