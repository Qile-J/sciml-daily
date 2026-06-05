# tests/test_scrape.py
import scrape

# arXiv's daily RSS feed (rss.arxiv.org): one call lists this mailing's new/cross/replace items.
ARXIV_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
 <channel>
  <item>
   <title>A Neural Operator</title>
   <link>https://arxiv.org/abs/2406.01234</link>
   <description>arXiv:2406.01234v1 Announce Type: new
Abstract:   We learn operators for PDEs.  </description>
   <category>cs.LG</category>
   <category>math.NA</category>
   <pubDate>Tue, 03 Jun 2026 00:00:00 -0400</pubDate>
   <dc:creator>Jane Doe, John Roe</dc:creator>
   <arxiv:announce_type>new</arxiv:announce_type>
  </item>
  <item>
   <title>An Old Paper, Revised</title>
   <link>https://arxiv.org/abs/2401.00001</link>
   <description>arXiv:2401.00001v3 Announce Type: replace
Abstract: A revision of an older paper.</description>
   <category>cs.LG</category>
   <pubDate>Tue, 03 Jun 2026 00:00:00 -0400</pubDate>
   <dc:creator>Someone Else</dc:creator>
   <arxiv:announce_type>replace</arxiv:announce_type>
  </item>
 </channel>
</rss>"""

def test_parse_arxiv():
    out = scrape.parse_arxiv(ARXIV_RSS)
    assert [p["id"] for p in out] == ["arxiv:2406.01234"]   # 'replace' revision dropped
    p = out[0]
    assert p["source"] == "arXiv"
    assert p["title"] == "A Neural Operator"
    assert p["abstract"] == "We learn operators for PDEs."
    assert p["categories"] == ["cs.LG", "math.NA"]
    assert p["authors"] == ["Jane Doe", "John Roe"]
    assert p["url"] == "https://arxiv.org/abs/2406.01234"
    assert p["published"] == "2026-06-03"

def test_fetch_arxiv_one_call_new_and_cross_only():
    out = scrape.fetch_arxiv(get=lambda: ARXIV_RSS)        # one RSS call, no date window
    assert [p["id"] for p in out] == ["arxiv:2406.01234"]

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
    assert p["published"] == "2024-06-03"   # cdate ms -> UTC day

def test_fetch_openreview_is_defensive():
    def boom(venue):
        raise RuntimeError("down")
    assert scrape.fetch_openreview(["X"], fetch=boom) == []

def test_is_candidate():
    assert scrape.is_candidate({"title": "Neural operator", "abstract": "for PDEs"}) is True
    assert scrape.is_candidate({"title": "Cake recipe", "abstract": "baking"}) is False
