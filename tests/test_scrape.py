# tests/test_scrape.py
import scrape

ARXIV_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <id>http://arxiv.org/abs/2406.01234v1</id>
  <title>A Neural Operator</title>
  <summary>  We learn operators for PDEs.  </summary>
  <published>2026-06-03T00:00:00Z</published>
  <author><name>Jane Doe</name></author>
  <category term="cs.LG"/><category term="math.NA"/>
 </entry>
</feed>"""
EMPTY = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'

def test_parse_arxiv():
    p = scrape.parse_arxiv(ARXIV_XML)[0]
    assert p["id"] == "arxiv:2406.01234"
    assert p["source"] == "arXiv"
    assert p["title"] == "A Neural Operator"
    assert p["abstract"] == "We learn operators for PDEs."
    assert p["categories"] == ["cs.LG", "math.NA"]
    assert p["authors"] == ["Jane Doe"]
    assert p["url"] == "https://arxiv.org/abs/2406.01234"
    assert p["published"] == "2026-06-03"

def test_fetch_arxiv_paginates_and_windows():
    pages = [ARXIV_XML, EMPTY]
    starts = []
    def get(start):
        starts.append(start)
        return pages[min(len(starts) - 1, 1)]
    out = scrape.fetch_arxiv("2026-06-01", get=get, sleep=lambda s: None)
    assert [p["id"] for p in out] == ["arxiv:2406.01234"]
    assert starts == [0, 100]

def test_fetch_arxiv_excludes_before_window():
    def get(start):
        return ARXIV_XML if start == 0 else ""
    out = scrape.fetch_arxiv("2026-06-05", get=get, sleep=lambda s: None)
    assert out == []

OR_PAYLOAD = {"notes": [{"id": "abc", "cdate": 1717372800000, "content": {
    "title": {"value": "Operator Learning"},
    "abstract": {"value": "Neural operators."},
    "authors": {"value": ["A One", "B Two"]}}}]}

def test_parse_openreview():
    p = scrape.parse_openreview(OR_PAYLOAD, "ICLR.cc/2026/Conference")[0]
    assert p["id"] == "openreview:abc"
    assert p["source"] == "OpenReview"
    assert p["title"] == "Operator Learning"
    assert p["authors"] == ["A One", "B Two"]
    assert p["url"] == "https://openreview.net/forum?id=abc"
    assert p["categories"] == ["ICLR.cc/2026/Conference"]

def test_fetch_openreview_is_defensive():
    def boom(venue):
        raise RuntimeError("down")
    assert scrape.fetch_openreview(["X"], fetch=boom) == []

def test_is_candidate():
    assert scrape.is_candidate({"title": "Neural operator", "abstract": "for PDEs"}) is True
    assert scrape.is_candidate({"title": "Cake recipe", "abstract": "baking"}) is False
