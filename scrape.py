# scrape.py
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
import requests
import config

ARX = "{http://arxiv.org/schemas/atom}"
DC = "{http://purl.org/dc/elements/1.1/}"

def _clean(s):
    return " ".join(s.split()) if s else ""

# ---------- arXiv (ONE daily RSS call across all categories) ----------
# rss.arxiv.org is CDN-served and built for daily polling — unlike the export query API it does
# not 429 from shared/CI IPs. The feed already IS "this mailing's new papers", so no date window,
# no pagination, no max_results. We keep `new` + `cross` items and drop `replace`/`replace-cross`
# (those are revisions of older papers, not new arrivals).
def parse_arxiv(xml_text):
    ch = ET.fromstring(xml_text).find("channel")
    out = []
    for it in (ch.findall("item") if ch is not None else []):
        if (it.findtext(f"{ARX}announce_type") or "").strip() not in ("new", "cross"):
            continue
        aid = re.sub(r"v\d+$", "", (it.findtext("link") or "").rsplit("/abs/", 1)[-1])
        if not aid:
            continue
        desc = it.findtext("description") or ""
        abstract = desc.split("Abstract:", 1)[-1] if "Abstract:" in desc else desc
        out.append({
            "id": f"arxiv:{aid}", "source": "arXiv",
            "title": _clean(it.findtext("title")),
            "abstract": _clean(abstract),
            "categories": [c.text for c in it.findall("category") if c.text],
            "authors": [a.strip() for a in (it.findtext(f"{DC}creator") or "").split(",") if a.strip()],
            "url": f"https://arxiv.org/abs/{aid}",
            "published": _rss_day(it.findtext("pubDate")),
        })
    return out

def _rss_day(s):
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""

def _arxiv_get():
    """One RSS request for today's announcements across all categories."""
    url = "https://rss.arxiv.org/rss/" + "+".join(config.ARXIV_CATEGORIES)
    r = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=60)
    r.raise_for_status()          # never swallow a failed fetch into an empty day
    return r.text

def fetch_arxiv(get=None):
    """One RSS call -> this mailing's new + cross-listed papers (self-bounded to today)."""
    return parse_arxiv((get or _arxiv_get)())

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
    """Deduped papers from arXiv + OpenReview. The arXiv RSS feed is already today's mailing,
    so no date filter there; `since` only bounds OpenReview (whose notes span all submissions)."""
    papers = fetch_arxiv()
    if config.OPENREVIEW:
        papers += [p for p in fetch_openreview(config.OPENREVIEW_VENUES) if p["published"] >= since]
    seen, out = set(), []
    for p in papers:
        if p["id"] not in seen:
            seen.add(p["id"])
            out.append(p)
    return out
