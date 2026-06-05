"""Single source of truth. The TAGS slugs must match prompts/classify.md."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"                       # GitHub Pages serves from here
PROMPT = ROOT / "prompts" / "classify.md"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
PAPERS_FILE = DATA / "papers.json"         # the feed + the only "seen" record (dedup by id)
STATS_FILE = DATA / "stats.json"           # maintainer-only run log (not shown on the site)

# arXiv: generous but specific categories. Pulled in ONE daily RSS call (rss.arxiv.org), which
# lists exactly this mailing's new/cross-listed papers (~500/day across this set). Edit freely.
ARXIV_CATEGORIES = [
    "cs.LG", "cs.NA", "cs.AI", "cs.CL", "cs.CE", "stat.ML",
    "math.NA", "math.OC", "math.DS", "math.AP", "math.PR", "math-ph",
    "physics.comp-ph", "physics.flu-dyn", "eess.SY",
]
USER_AGENT = "sciml-daily/1.0 (+https://github.com/qile-j/sciml-daily; mailto:qile.jiang@outlook.com)"
# OpenReview-only date window (days): its notes span all submissions ever, so we keep only those
# created in the last couple days. arXiv needs no window — its RSS feed is already today's mailing.
FETCH_WINDOW_DAYS = 2

# OpenReview (set OPENREVIEW = False to skip)
OPENREVIEW = True
OPENREVIEW_VENUES = ["ICLR.cc/2026/Conference", "NeurIPS.cc/2025/Conference"]

# DeepSeek — the only model (cheap paid API). Bump this one line for new versions.
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
BATCH_SIZE = 30                            # papers per request (batched to cut latency + cost)
MAX_TOKENS = 8192                          # generous output cap so a full batch is never truncated
MAX_REQUESTS = 200                         # per-run safety cap so a spike can't run up the bill
REQUEST_DELAY = 1.0                        # small gap between calls (DeepSeek allows fast sequential use)

# Subfield tags: slug -> (display name, pill color). Keep slugs in sync with prompts/classify.md.
TAGS = {
    "operator-learning":                    ("Operator Learning",         "#6366f1"),
    "pde-foundation-models":                ("PDE Foundation Models",     "#0ea5e9"),
    "physics-informed-ml":                  ("Physics-Informed ML",       "#14b8a6"),
    "generative-simulation":                ("Generative Simulation",     "#ec4899"),
    "differentiable-simulation":            ("Differentiable Simulation", "#f59e0b"),
    "ml-numerical-methods":                 ("ML Numerical Methods",      "#8b5cf6"),
    "equation-discovery-dynamical-systems": ("Equation Discovery",        "#10b981"),
    "llm-agents-for-sci-computing":         ("LLM Agents for SciComp",    "#ef4444"),
    "uq-inverse-problems":                  ("UQ & Inverse Problems",     "#3b82f6"),
    "foundations":                          ("Foundations",               "#64748b"),
    "mathematical-analysis-of-llm":         ("Math Analysis of LLMs",     "#a855f7"),
}

# Prefilter keywords (lowercased substring match; recall-first, the LLM enforces precision).
KEYWORDS = [
    "neural operator", "fourier neural operator", "deeponet", "operator learning",
    "physics-informed", "physics informed", "pinn", "pino", "deep energy method",
    "pde", "partial differential equation", "differential equation",
    "surrogate model", "reduced-order", "reduced order model", "emulator",
    "differentiable simulation", "differentiable physics", "differentiable solver",
    "scientific machine learning", "scientific computing",
    "numerical method", "numerical analysis", "finite element", "finite difference",
    "spectral method", "preconditioner", "linear solver",
    "symbolic regression", "sindy", "equation discovery", "koopman", "neural ode",
    "dynamical system", "data assimilation", "inverse problem",
    "uncertainty quantification", "gaussian process",
    "diffusion model", "generative model", "turbulence", "navier-stokes",
    "foundation model", "large language model", " llm", "transformer", "attention",
    "autoformalization", "theorem proving", "mean-field", "mean field",
    "markov chain", "generalization bound", "in-context learning", "expressivity",
    "approximation theory", "convergence rate", "neural network",
]

SITE_TITLE = "SciML Daily"
SITE_TAGLINE = "New papers in Scientific ML, AI for Scientific Computing & Applied Math — every morning."
SITE_URL = "https://qile-j.github.io/sciml-daily"   # your Pages URL (used in links + RSS)
RSS_COUNT = 60
