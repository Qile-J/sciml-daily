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
