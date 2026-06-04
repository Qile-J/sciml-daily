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
    assert "Wednesday, June 3, 2026" in idx        # pretty date
    assert (out / "day" / "2026-06-03.html").exists()
    assert (out / "archive.html").exists()
    assert "Neural Operator X" in (out / "feed.xml").read_text()
    assert (out / "static" / "style.css").exists()

def test_build_empty_still_writes_index(tmp_path):
    out = tmp_path / "docs"
    build.build([], out=out)
    assert (out / "index.html").exists()
