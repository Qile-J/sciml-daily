# build.py
import json
import shutil
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
import config

def load_papers():
    if config.PAPERS_FILE.exists():
        return json.loads(config.PAPERS_FILE.read_text(encoding="utf-8"))
    return []

def _group_by_day(papers):
    days = {}
    for p in papers:
        days.setdefault(p["added"], []).append(p)
    return dict(sorted(days.items(), reverse=True))   # newest day first

def build(papers, out=None):
    out = out or config.DOCS
    env = Environment(loader=FileSystemLoader(str(config.TEMPLATES)),
                      autoescape=select_autoescape(["html", "xml"]))
    env.filters["pretty"] = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%A, %B %-d, %Y")

    days = _group_by_day(papers)
    day_list = list(days.keys())
    tags = {slug: {"name": n, "color": c} for slug, (n, c) in config.TAGS.items()}
    ctx = dict(site_title=config.SITE_TITLE, tagline=config.SITE_TAGLINE,
               url=config.SITE_URL.rstrip("/"), tags=tags, days=day_list)

    (out / "day").mkdir(parents=True, exist_ok=True)
    page = env.get_template("page.html")
    for d, ps in days.items():
        (out / "day" / f"{d}.html").write_text(page.render(**ctx, day=d, papers=ps), encoding="utf-8")

    latest = day_list[0] if day_list else None
    (out / "index.html").write_text(
        page.render(**ctx, day=latest, papers=days.get(latest, [])), encoding="utf-8")

    (out / "archive.html").write_text(
        env.get_template("archive.html").render(**ctx, counts=[(d, len(days[d])) for d in day_list]),
        encoding="utf-8")

    recent = sorted(papers, key=lambda p: p["added"], reverse=True)[:config.RSS_COUNT]
    (out / "feed.xml").write_text(
        env.get_template("feed.xml").render(**ctx, papers=recent), encoding="utf-8")

    dst = out / "static"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(config.STATIC, dst)
