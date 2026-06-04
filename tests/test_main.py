# tests/test_main.py
import json
import main, config, scrape

def _wire(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PAPERS_FILE", tmp_path / "papers.json")
    monkeypatch.setattr(config, "STATS_FILE", tmp_path / "stats.json")
    monkeypatch.setattr(config, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(config, "REQUEST_DELAY", 0)   # skip pacing in tests

def test_run_end_to_end_offline(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch)
    fetched = [
        {"id": "arxiv:1", "source": "arXiv", "title": "Neural operator", "abstract": "pde surrogate",
         "categories": ["cs.LG"], "authors": ["X"], "url": "u", "published": "2026-06-04"},
        {"id": "arxiv:2", "source": "arXiv", "title": "cooking", "abstract": "cakes",
         "categories": ["cs.LG"], "authors": ["Y"], "url": "u", "published": "2026-06-04"},
    ]
    monkeypatch.setattr(scrape, "fetch_all", lambda since: fetched)
    def gen(instr, msg):
        return '[{"id":1,"in_scope":true,"tags":["operator-learning"],"reason":"r"}]'
    main.run(today="2026-06-04", generate=gen, balance=lambda: "CNY 19.7")

    papers = json.loads((tmp_path / "papers.json").read_text())
    assert [p["id"] for p in papers] == ["arxiv:1"]          # candidate + in-scope only
    assert papers[0]["added"] == "2026-06-04"
    assert (tmp_path / "docs" / "index.html").read_text().count("Neural operator") >= 1

    stats = json.loads((tmp_path / "stats.json").read_text())
    assert stats[-1]["candidates"] == 1 and stats[-1]["in_scope"] == 1
    assert stats[-1]["requests"] == 1 and stats[-1]["balance_after"] == "CNY 19.7"

def test_run_dedups_against_feed(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch)
    fetched = [{"id": "arxiv:1", "source": "arXiv", "title": "Neural operator", "abstract": "pde",
                "categories": ["cs.LG"], "authors": ["X"], "url": "u", "published": "2026-06-04"}]
    monkeypatch.setattr(scrape, "fetch_all", lambda since: fetched)
    calls = {"n": 0}
    def gen(instr, msg):
        calls["n"] += 1
        return '[{"id":1,"in_scope":true,"tags":[],"reason":"r"}]'
    main.run(today="2026-06-04", generate=gen, balance=lambda: None)
    main.run(today="2026-06-05", generate=gen, balance=lambda: None)   # same paper re-fetched
    assert calls["n"] == 1                                   # already in papers.json -> not re-classified
    assert len(json.loads((tmp_path / "papers.json").read_text())) == 1
