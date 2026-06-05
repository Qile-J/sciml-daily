# build.py
import json
import shutil
from jinja2 import Environment, FileSystemLoader, select_autoescape
import config

def load_papers():
    if config.PAPERS_FILE.exists():
        return json.loads(config.PAPERS_FILE.read_text(encoding="utf-8"))
    return []

# Fields shipped to the browser in data.json. Internal fields (reason, in_scope,
# categories, published) are deliberately omitted; `summary` replaces `reason`.
CARD_FIELDS = ("id", "title", "authors", "tags", "url", "source", "abstract", "added")

def _card(p):
    card = {k: p.get(k) for k in CARD_FIELDS}
    card["summary"] = p.get("summary") or p.get("reason") or ""
    return card

def build(papers, out=None):
    out = out or config.DOCS
    out.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(config.TEMPLATES)),
                      autoescape=select_autoescape(["html", "xml"]))

    tags = {slug: {"name": n, "color": c} for slug, (n, c) in config.TAGS.items()}
    ordered = sorted(papers, key=lambda p: p.get("added", ""), reverse=True)  # newest first
    data = {"tags": tags, "papers": [_card(p) for p in ordered]}
    (out / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    page = env.get_template("page.html")
    (out / "index.html").write_text(
        page.render(site_title=config.SITE_TITLE, tagline=config.SITE_TAGLINE), encoding="utf-8")

    dst = out / "static"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(config.STATIC, dst)
