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

def _load_seen():
    return set(config.SEEN_FILE.read_text().split()) if config.SEEN_FILE.exists() else set()

def _append_seen(ids):
    config.SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.SEEN_FILE, "a") as f:
        for i in ids:
            f.write(i + "\n")

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
    since = (date.fromisoformat(today) - timedelta(days=config.LOOKBACK_DAYS)).isoformat()
    generate = generate or classify.deepseek_generate
    balance = balance or classify.deepseek_balance

    bal_start = balance()
    seen = _load_seen()
    fetched = scrape.fetch_all(since)
    new = [p for p in fetched if p["id"] not in seen]
    candidates = [p for p in new if scrape.is_candidate(p)]
    non_candidates = [p["id"] for p in new if not scrape.is_candidate(p)]
    print(f"[main] fetched {len(fetched)} · new {len(new)} · candidates {len(candidates)}")

    classified, used = classify.classify(candidates, generate) if candidates else ([], 0)
    in_scope = [{**p, "added": today} for p in classified if p["in_scope"]]
    deferred = len(candidates) - len(classified)

    papers = build.load_papers() + in_scope
    config.PAPERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.PAPERS_FILE.write_text(json.dumps(papers, indent=1, ensure_ascii=False), encoding="utf-8")
    _append_seen(non_candidates + [p["id"] for p in classified])
    build.build(papers)

    bal_end = balance()
    _log_run({"date": today, "fetched": len(fetched), "new": len(new),
              "candidates": len(candidates), "classified": len(classified),
              "in_scope": len(in_scope), "deferred": deferred, "requests": used,
              "balance_before": bal_start, "balance_after": bal_end, "total_papers": len(papers)})

    print("[main] ───── run summary ─────")
    print(f"[main] candidates {len(candidates)} · classified {len(classified)} · "
          f"in-scope {len(in_scope)} · deferred {deferred} (retry next run)")
    print(f"[main] DeepSeek requests this run: {used}")
    print(f"[main] balance: {bal_start} -> {bal_end}")
    print(f"[main] site now lists {len(papers)} papers. done.")

if __name__ == "__main__":
    run()
