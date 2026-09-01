"""Contract Analyzer Agent.

Extracts parties, dates, obligations, and risk flags from a free-form
contract, and assigns an overall risk score.
"""

import json
import re
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class ContractReport(BaseModel):
    parties: List[str]
    effective_date: str
    term: str
    key_obligations: List[str]
    risk_flags: List[str]
    risk_score: int
    summary: str


_DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(r"\b(?:January|February|March|April|May|June|July|"
               r"August|September|October|November|December)\s+"
               r"\d{1,2},?\s+\d{4}\b"),
]

_RISK_PATTERNS = [
    ("auto-renew", re.compile(r"auto(?:matic(?:ally)?)?[- ]?renew", re.I)),
    ("unilateral termination", re.compile(r"terminate (?:this )?agreement (?:at any time|for convenience)", re.I)),
    ("indemnification", re.compile(r"\bindemnif", re.I)),
    ("liability cap absent", re.compile(r"unlimited liability", re.I)),
    ("non-compete", re.compile(r"non[- ]compete", re.I)),
    ("exclusivity", re.compile(r"\bexclusiv(e|ity)\b", re.I)),
    ("assignment without consent", re.compile(r"assign (?:this )?agreement without (?:the )?consent", re.I)),
    ("jurisdiction / venue", re.compile(r"governed by the laws of", re.I)),
    ("liquidated damages", re.compile(r"liquidated damages", re.I)),
    ("ip assignment", re.compile(r"assigns? (?:all )?(?:right|title|interest) in", re.I)),
]

_PARTY_HINTS = re.compile(
    r"\b(between|by and between|among)\s+([A-Z][\w&.,\- ]{1,80}?)"
    r"(?:\s+(?:and|&)\s+([A-Z][\w&.,\- ]{1,80})){1,3}",
)

_OBLIGATION_VERBS = (
    "shall", "must", "agrees to", "will", "is required to", "is obligated to",
)


def extract_dates(text: str) -> dict:
    """Return every date-like string found in the contract."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    found = set()
    for p in _DATE_PATTERNS:
        for m in p.findall(text):
            found.add(m)
    return {"status": "ok", "dates": sorted(found), "count": len(found)}


def extract_parties(text: str) -> dict:
    """Heuristically extract the contracting parties."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    parties = []
    m = _PARTY_HINTS.search(text)
    if m:
        for g in m.groups()[1:]:
            if g and g not in parties:
                parties.append(g.strip(" ,.;"))
    for line in text.splitlines()[:20]:
        if re.match(r"\s*([A-Z][\w &.,'-]{2,80})\s*\(", line):
            name = line.split("(", 1)[0].strip()
            if name and name not in parties:
                parties.append(name)
    return {"status": "ok", "parties": parties, "count": len(parties)}


def extract_obligations(text: str, max_items: int = 10) -> dict:
    """Pull obligation-bearing sentences from the contract."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    out: List[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    for s in sentences:
        low = s.lower()
        if any(v in low for v in _OBLIGATION_VERBS):
            out.append(s.strip())
        if len(out) >= max_items:
            break
    return {"status": "ok", "obligations": out, "count": len(out)}


def detect_risk_flags(text: str) -> dict:
    """Flag clauses that often warrant legal review."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    flags = []
    for label, pat in _RISK_PATTERNS:
        m = pat.search(text)
        if m:
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            flags.append({
                "flag": label,
                "snippet": text[start:end].replace("\n", " "),
            })
    return {"status": "ok", "flags": flags, "count": len(flags)}


def term(text: str) -> dict:
    """Try to extract the term length ("3 years", "12 months")."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    pat = re.compile(
        r"\b(term|period) (?:of )?(\d{1,3})\s+(year|years|month|months|day|days)\b",
        re.I,
    )
    m = pat.search(text)
    if not m:
        return {"status": "ok", "term": "unspecified"}
    return {"status": "ok", "term": f"{m.group(2)} {m.group(3)}"}


def risk_score(flags_json: str) -> dict:
    """Convert a flag list into a 0-100 risk score."""
    try:
        flags = json.loads(flags_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    weights = {
        "unlimited liability": 30,
        "indemnification": 15,
        "auto-renew": 10,
        "non-compete": 12,
        "exclusivity": 12,
        "assignment without consent": 10,
        "liquidated damages": 8,
        "ip assignment": 8,
        "unilateral termination": 10,
        "jurisdiction / venue": 5,
    }
    score = sum(weights.get(f["flag"], 5) for f in flags)
    score = min(100, score)
    label = "high" if score >= 50 else "medium" if score >= 20 else "low"
    return {"status": "ok", "score": score, "label": label}


def analyze(text: str) -> dict:
    """One-call combined contract analysis."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    parties = extract_parties(text)
    dates = extract_dates(text)
    oblig = extract_obligations(text)
    flags = detect_risk_flags(text)
    term_info = term(text)
    score = risk_score(json.dumps(flags.get("flags", [])))
    return {
        "status": "ok",
        "parties": parties.get("parties", []),
        "effective_date": (dates.get("dates", []) or ["unknown"])[0],
        "term": term_info.get("term", "unspecified"),
        "key_obligations": oblig.get("obligations", []),
        "risk_flags": flags.get("flags", []),
        "risk_score": score.get("score", 0),
        "risk_label": score.get("label", "low"),
        "summary": f"Contract between {', '.join(parties.get('parties', [])) or 'unknown parties'} "
                   f"with {len(oblig.get('obligations', []))} key obligations and "
                   f"{len(flags.get('flags', []))} risk flags.",
    }


root_agent = Agent(
    name="contract_analyzer_agent",
    model="gemini-2.0-flash",
    description=(
        "Extracts parties, dates, obligations and risk flags from "
        "a contract, and assigns an overall risk score."
    ),
    instruction="""
    You are a paralegal-style contract reviewer.

    WORKFLOW for every contract:
    1. Call `analyze` (which calls all sub-tools internally) to
       produce a complete structured report.
    2. Present the result in this order:
         a) Parties, effective date, term.
         b) Top 5 key obligations (truncate for readability).
         c) Risk flags (with snippets and a 1-line explanation of
            why each matters).
         d) Overall risk score (0-100) and label.
         e) A 1-paragraph plain-English summary.
    3. If the risk score is "high" or there are > 5 risk flags,
       explicitly recommend that a licensed attorney review the
       document.

    RULES:
    - Never give legal advice. Frame recommendations as
       "consider consulting a lawyer".
    - Snippets must be verbatim from the source; do not paraphrase.
    - If a field can't be extracted, say "not found" rather than
       guess.
    """,
    tools=[
        extract_dates, extract_parties, extract_obligations,
        detect_risk_flags, term, risk_score, analyze,
    ],
    output_schema=ContractReport,
    output_key="contract",
)
