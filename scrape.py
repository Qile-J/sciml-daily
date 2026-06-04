# scrape.py
import time
import urllib.parse
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import requests
import config

ATOM = "{http://www.w3.org/2005/Atom}"
EMPTY_FEED = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'

def _clean(s):
    return " ".join(s.split()) if s else ""

# ---------- arXiv ----------
def parse_arxiv(xml_text):
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall(f"{ATOM}entry"):
        aid = (e.findtext(f"{ATOM}id") or "").rsplit("/abs/", 1)[-1].split("v")[0]
        out.append({
            "id": f"arxiv:{aid}", "source": "arXiv",
            "title": _clean(e.findtext(f"{ATOM}title")),
            "abstract": _clean(e.findtext(f"{ATOM}summary")),
            "categories": [c.get("term") for c in e.findall(f"{ATOM}category") if c.get("term")],
            "authors": [a for a in (_clean(x.findtext(f"{ATOM}name"))
                                    for x in e.findall(f"{ATOM}author")) if a],
            "url": f"https://arxiv.org/abs/{aid}",
            "published": (e.findtext(f"{ATOM}published") or "")[:10],
        })
    return out

def _arxiv_get(start):
    q = urllib.parse.urlencode({
        "search_query": "(" + " OR ".join(f"cat:{c}" for c in config.ARXIV_CATEGORIES) + ")",
        "start": start, "max_results": 100,
        "sortBy": "submittedDate", "sortOrder": "descending"})
    r = requests.get(f"http://export.arxiv.org/api/query?{q}",
                     headers={"User-Agent": "sciml-daily/1.0"}, timeout=60)
    return r.text if r.ok else ""

def fetch_arxiv(since, get=None, sleep=time.sleep):
    """Newest-first pages until we cross below `since` (YYYY-MM-DD)."""
    get = get or _arxiv_get
    papers, start = [], 0
    while start < 2000:
        batch = parse_arxiv(get(start) or EMPTY_FEED)
        if not batch:
            break
        papers += batch
        if batch[-1]["published"] < since:
            break
        start += 100
        sleep(3)                       # arXiv API politeness
    return [p for p in papers if p["published"] >= since]

# ---------- OpenReview ----------
def _val(content, key, default=""):
    f = content.get(key)
    return f.get("value", default) if isinstance(f, dict) else (f if f is not None else default)

def _ms_day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d") if ms else ""

def parse_openreview(payload, venue):
    out = []
    for n in payload.get("notes", []):
        c = n.get("content", {})
        title, abstract = _val(c, "title"), _val(c, "abstract")
        if not title or not abstract:
            continue
        out.append({
            "id": f"openreview:{n['id']}", "source": "OpenReview",
            "title": str(title).strip(), "abstract": str(abstract).strip(),
            "categories": [venue], "authors": list(_val(c, "authors", []) or []),
            "url": f"https://openreview.net/forum?id={n['id']}",
            "published": _ms_day(n.get("cdate")),
        })
    return out

def _or_fetch(venue):
    r = requests.get("https://api2.openreview.net/notes",
                     params={"content.venueid": venue, "limit": 1000}, timeout=60)
    r.raise_for_status()
    return r.json()

def fetch_openreview(venues, fetch=None):
    fetch = fetch or _or_fetch
    out = []
    for v in venues:
        try:
            out += parse_openreview(fetch(v), v)
        except Exception as e:            # one bad venue must not kill the run
            print(f"[openreview] skip {v}: {e}")
    return out

# ---------- combine + prefilter ----------
_KW = [k.lower() for k in config.KEYWORDS]

def is_candidate(p):
    text = (p["title"] + " " + p["abstract"]).lower()
    return any(k in text for k in _KW)

def fetch_all(since):
    """Deduped list of papers published on/after `since` (arXiv + OpenReview).
    The date window is applied to both sources so a daily `since=today` means today only."""
    papers = fetch_arxiv(since)
    if config.OPENREVIEW:
        papers += fetch_openreview(config.OPENREVIEW_VENUES)
    seen, out = set(), []
    for p in papers:
        if p["published"] >= since and p["id"] not in seen:
            seen.add(p["id"])
            out.append(p)
    return out
