"""Lead Enrichment Agent.

Takes a partial lead (name + company, or just a domain) and produces
a fully-enriched profile with company size, industry guess, tech-stack
hints, and a lead score.
"""

import json
import re
import urllib.error
import urllib.request
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class LeadProfile(BaseModel):
    name: str
    company: str
    domain: str
    industry: str
    company_size_guess: str
    tech_stack: List[str]
    recent_news: List[str]
    lead_score: int
    rationale: str


_INDUSTRY_HINTS = {
    "saas":       ("software", "saas", "platform", "cloud", "api"),
    "ecommerce":  ("shop", "store", "ecom", "retail", "merch"),
    "finance":    ("bank", "capital", "finance", "invest", "pay"),
    "healthcare": ("health", "medical", "clinic", "pharma", "bio"),
    "media":      ("media", "news", "studio", "press", "publishing"),
    "education":  ("academy", "edu", "learn", "school", "university"),
    "manufacturing": ("industries", "manufactur", "factory", "industrial"),
}

_TECH_HINTS = (
    "aws", "gcp", "azure", "kubernetes", "docker", "terraform",
    "python", "node", "react", "vue", "django", "flask", "fastapi",
    "postgres", "mysql", "mongodb", "redis", "kafka", "snowflake",
    "stripe", "twilio", "segment", "datadog", "okta", "auth0",
    "hubspot", "salesforce", "intercom", "zendesk", "shopify",
    "wordpress", "magento", "cloudflare", "fastly", "vercel",
    "netlify", "heroku", "digitalocean", "cloudfront", "s3",
)

_HEADCOUNT_HINTS = {
    "1-10":      ("solo", "startup", "founder", "we are a small"),
    "11-50":     ("growing team", "small team"),
    "51-200":    ("scaling", "mid-size"),
    "201-1000":  ("hundreds of", "global team"),
    "1000+":     ("thousands of", "fortune", "global enterprise"),
}

_TIMEOUT = 12
_USER_AGENT = "ADK-LeadEnricher/1.0"


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read(200_000).decode("utf-8", errors="replace")


def normalize_domain(input_str: str) -> dict:
    """Clean up a domain or URL into a canonical hostname."""
    if not input_str:
        return {"status": "error", "error": "input is required."}
    s = input_str.strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = s.split("/", 1)[0]
    s = s.lstrip("www.")
    if "." not in s:
        return {"status": "error", "error": "not a domain."}
    return {"status": "ok", "domain": s}


def fetch_homepage(domain: str) -> dict:
    """Download a homepage and return a cleaned text snippet."""
    d = normalize_domain(domain)
    if d["status"] != "ok":
        return d
    url = f"https://{d['domain']}/"
    try:
        html = _http_get(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "error", "error": f"fetch failed: {exc}"}
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return {"status": "ok", "url": url, "text": text[:8000], "char_count": len(text)}


def guess_industry(text: str) -> dict:
    """Heuristically pick an industry from site copy."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    low = text.lower()
    scores = {k: 0 for k in _INDUSTRY_HINTS}
    for industry, hints in _INDUSTRY_HINTS.items():
        for h in hints:
            scores[industry] += low.count(h)
    best = max(scores.items(), key=lambda kv: kv[1])
    label = best[0] if best[1] > 0 else "unknown"
    return {"status": "ok", "industry": label, "scores": scores}


def detect_tech_stack(text: str) -> dict:
    """Scan homepage text for technology mentions."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    low = text.lower()
    hits = sorted({h for h in _TECH_HINTS if h in low})
    return {"status": "ok", "tech_stack": hits, "count": len(hits)}


def guess_company_size(text: str) -> dict:
    """Heuristically estimate headcount bucket from site copy."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    low = text.lower()
    for bucket, hints in _HEADCOUNT_HINTS.items():
        for h in hints:
            if h in low:
                return {"status": "ok", "size_bucket": bucket, "matched": h}
    return {"status": "ok", "size_bucket": "unknown"}


def extract_recent_news(domain: str) -> dict:
    """Try to surface recent press mentions via the Google News RSS."""
    d = normalize_domain(domain)
    if d["status"] != "ok":
        return d
    url = f"https://news.google.com/rss/search?q={d['domain']}&hl=en-US"
    try:
        raw = _http_get(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "error", "error": f"news fetch failed: {exc}"}
    items: List[str] = []
    for block in re.findall(r"<item>(.*?)</item>", raw, re.DOTALL):
        title_m = re.search(r"<title>(.*?)</title>", block, re.DOTALL)
        if title_m:
            items.append(re.sub(r"\s+", " ", title_m.group(1)).strip())
        if len(items) >= 5:
            break
    return {"status": "ok", "items": items, "count": len(items)}


def lead_score(industry_json: str, tech_json: str, size_json: str,
               news_json: str) -> dict:
    """Combine the sub-signals into a 0-100 lead score."""
    try:
        industry = json.loads(industry_json).get("industry", "unknown")
        tech = json.loads(tech_json).get("tech_stack", [])
        size = json.loads(size_json).get("size_bucket", "unknown")
        news = json.loads(news_json).get("items", [])
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    score = 0
    if industry != "unknown":
        score += 25
    if 1 <= len(tech) <= 30:
        score += 25
    if size in {"51-200", "201-1000", "1000+"}:
        score += 25
    elif size in {"11-50"}:
        score += 15
    score += min(25, len(news) * 5)
    score = min(100, score)
    if score >= 75:
        label = "hot"
    elif score >= 50:
        label = "warm"
    else:
        label = "cold"
    return {"status": "ok", "score": score, "label": label}


def enrich(name: str, company: str, domain: str = "") -> dict:
    """One-call lead enrichment."""
    if not domain and company:
        s = re.sub(r"[^a-z0-9]+", "", company.lower())
        domain = f"{s}.com"
    d = normalize_domain(domain or "")
    if d["status"] != "ok":
        return d
    hp = fetch_homepage(d["domain"])
    if hp["status"] != "ok":
        return {"status": "ok", "name": name, "company": company,
                "domain": d["domain"], "industry": "unknown",
                "company_size_guess": "unknown", "tech_stack": [],
                "recent_news": [], "lead_score": 0,
                "rationale": f"homepage unreachable: {hp.get('error')}"}
    text = hp["text"]
    industry = guess_industry(text)
    tech = detect_tech_stack(text)
    size = guess_company_size(text)
    news = extract_recent_news(d["domain"])
    score = lead_score(json.dumps(industry), json.dumps(tech),
                       json.dumps(size), json.dumps(news))
    return {
        "status": "ok",
        "name": name,
        "company": company,
        "domain": d["domain"],
        "industry": industry.get("industry", "unknown"),
        "company_size_guess": size.get("size_bucket", "unknown"),
        "tech_stack": tech.get("tech_stack", []),
        "recent_news": news.get("items", []),
        "lead_score": score.get("score", 0),
        "lead_label": score.get("label", "cold"),
    }


root_agent = Agent(
    name="lead_enricher_agent",
    model="gemini-2.0-flash",
    description=(
        "Enriches a sales lead with industry guess, company size, "
        "tech-stack hints, recent news, and a 0-100 lead score."
    ),
    instruction="""
    You are a B2B sales-research assistant.

    WORKFLOW for every lead:
    1. Call `normalize_domain` on the user's input (domain, URL or
       company name).
    2. Call `fetch_homepage` to grab the cleaned homepage text.
    3. Call `guess_industry`, `detect_tech_stack`,
       `guess_company_size`, `extract_recent_news` in parallel.
    4. Call `lead_score` to compute the 0-100 score.
    5. (Optionally) call `enrich` to do the whole pipeline in one
       call when the user just gives you a name + company.

    DELIVERABLES:
    - A structured LeadProfile.
    - A 2-3 sentence rationale tying the score to specific
       evidence (e.g. "uses AWS + Segment, mid-size SaaS, 3 recent
       press mentions").
    - One concrete next step ("reach out with X", "send Y template").

    RULES:
    - Never invent company facts not returned by the tools.
    - If the homepage is unreachable, say so and return a "cold"
       score; don't fabricate a tech stack.
    - Respect robots.txt boundaries: only fetch the homepage, not
       internal pages.
    """,
    tools=[
        normalize_domain, fetch_homepage, guess_industry,
        detect_tech_stack, guess_company_size, extract_recent_news,
        lead_score, enrich,
    ],
    output_schema=LeadProfile,
    output_key="lead",
)
