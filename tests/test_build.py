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
