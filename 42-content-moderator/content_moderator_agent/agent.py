"""Content Moderator Agent.

Multi-signal moderation: lexicon-based toxicity, regex-based PII
detection, and policy-keyword matching. Produces a 0-100 risk score
and per-finding snippets.
"""

import re
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class ModerationReport(BaseModel):
    risk_score: int
    risk_label: str
    action: str
    toxicity_findings: List[str]
    pii_findings: List[str]
    policy_findings: List[str]
    redacted_text: str
    rationale: str


_TOXIC_WORDS = {
    "hate", "kill", "idiot", "stupid", "moron", "trash", "loser",
    "shut up", "die", "worthless", "disgusting", "scum", "vermin",
    "retard", "slur",
}
_PII_PATTERNS = {
    "email":     re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone":     re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"),
    "ssn":       re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "ipv4":      re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}
_POLICY_KEYWORDS = {
    "violence": ("weapon", "bomb", "shoot", "stab", "attack", "explosive"),
    "sexual":   ("nsfw", "porn", "explicit", "nude", "xxx"),
    "drugs":    ("cocaine", "heroin", "meth", "fentanyl"),
    "self_harm": ("suicide", "self-harm", "cut myself"),
    "spam":     ("click here", "free money", "buy now", "100% guaranteed"),
}


def detect_toxicity(text: str) -> dict:
    """Return matched toxic phrases with positions."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    low = text.lower()
    hits = []
    for phrase in _TOXIC_WORDS:
        for m in re.finditer(re.escape(phrase), low):
            hits.append({"phrase": phrase, "offset": m.start()})
    return {"status": "ok", "count": len(hits), "findings": hits}


def detect_pii(text: str) -> dict:
    """Return matched PII patterns with masked snippets."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    findings = []
    for kind, pat in _PII_PATTERNS.items():
        for m in pat.finditer(text):
            value = m.group(0)
            masked = value[:2] + "***" + value[-2:] if len(value) > 4 else "***"
            findings.append({"kind": kind, "offset": m.start(),
                             "masked": masked, "length": len(value)})
    return {"status": "ok", "count": len(findings), "findings": findings}


def detect_policy(text: str) -> dict:
    """Return policy-keyword matches grouped by category."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    low = text.lower()
    findings = []
    for cat, keywords in _POLICY_KEYWORDS.items():
        for kw in keywords:
            if kw in low:
                findings.append({"category": cat, "keyword": kw})
    return {"status": "ok", "count": len(findings), "findings": findings}


def redact(text: str, pii_json: Dict) -> dict:
    """Replace detected PII spans with category tags."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    spans = sorted(pii_json.get("findings", []), key=lambda f: f["offset"], reverse=True)
    out = text
    for s in spans:
        start = s["offset"]
        end = start + s["length"]
        tag = f"[{s['kind'].upper()}_REDACTED]"
        out = out[:start] + tag + out[end:]
    return {"status": "ok", "redacted": out}


def risk_score(tox_json: Dict, pii_json: Dict, policy_json: Dict) -> dict:
    """Combine the three signals into a 0-100 risk score."""
    t = tox_json.get("count", 0) if isinstance(tox_json, dict) else 0
    p = pii_json.get("count", 0) if isinstance(pii_json, dict) else 0
    k = policy_json.get("count", 0) if isinstance(policy_json, dict) else 0
    score = min(100, t * 8 + p * 12 + k * 15)
    label = "high" if score >= 60 else "medium" if score >= 25 else "low"
    action = ("block" if score >= 60
              else "review" if score >= 25
              else "approve")
    return {"status": "ok", "score": score, "label": label, "action": action}


def moderate(text: str) -> dict:
    """One-call moderation pipeline."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    tox = detect_toxicity(text)
    pii = detect_pii(text)
    pol = detect_policy(text)
    red = redact(text, pii)
    rs = risk_score(tox, pii, pol)
    return {
        "status": "ok",
        "risk_score": rs.get("score", 0),
        "risk_label": rs.get("label", "low"),
        "action": rs.get("action", "approve"),
        "toxicity_findings": [f["phrase"] for f in tox.get("findings", [])],
        "pii_findings": [f["kind"] for f in pii.get("findings", [])],
        "policy_findings": [f["category"] for f in pol.get("findings", [])],
        "redacted_text": red.get("redacted", text),
        "rationale": (
            f"toxicity={tox.get('count', 0)}, pii={pii.get('count', 0)}, "
            f"policy={pol.get('count', 0)} -> risk={rs.get('score', 0)} ({rs.get('label', 'low')})"
        ),
    }


root_agent = Agent(
    name="content_moderator_agent",
    model="gemini-2.0-flash",
    description=(
        "Three-signal content moderation: toxicity, PII and policy "
        "keyword matching, with redaction and a 0-100 risk score."
    ),
    instruction="""
    You are a community-safety moderator.

    WORKFLOW:
    1. Call `moderate` (which runs all three detectors and
       redaction in one pass) on the user's text.
    2. Present the result as:
         * Risk score and label.
         * Action (approve / review / block).
         * Counts per signal (toxicity, PII, policy).
         * The redacted text in a fenced block.
         * 1-2 sentence rationale.

    RULES:
    - Never recommend `approve` when the score is >= 25.
    - For PII, never echo the original value back to the user -
       show only the kind and the masked snippet.
    - If the user pushes back ("it's just a joke"), surface the
       matched phrase + policy category, then ask them to revise.
    - Keep responses neutral and procedural; do not moralise.
    """,
    tools=[
        detect_toxicity, detect_pii, detect_policy,
        redact, risk_score, moderate,
    ],
    output_schema=ModerationReport,
    output_key="moderation",
)
