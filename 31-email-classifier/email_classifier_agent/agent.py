"""Email Classifier Agent.

Triage an inbox: classify each message by priority and category,
extract action items, and (optionally) draft a reply.
"""

import json
import re
from collections import Counter
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class EmailClass(BaseModel):
    from_: str = Field(alias="from")
    subject: str
    category: str
    priority: str
    action_required: bool
    action_items: List[str]
    draft_reply: str
    reasoning: str

    class Config:
        populate_by_name = True


_URGENT_RE = re.compile(
    r"\b(asap|urgent|important|eod|eow|today|now|critical|action required)\b",
    re.IGNORECASE,
)
_CATEGORIES = {
    "work": ("meeting", "project", "deadline", "report", "client", "deliverable"),
    "personal": ("birthday", "family", "friend", "dinner", "weekend"),
    "finance": ("invoice", "payment", "refund", "tax", "bank", "wire"),
    "support": ("issue", "bug", "help", "ticket", "outage", "error"),
    "newsletter": ("unsubscribe", "newsletter", "digest", "weekly"),
    "spam": ("free", "winner", "congratulations", "click here", "limited offer"),
}
_NOISE = re.compile(r"^(\s*[\-=]\s*)+$")


def _strip_headers(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        if _NOISE.match(line):
            continue
        if re.match(r"^(From|To|Cc|Bcc|Subject|Date):\s", line, re.IGNORECASE):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def parse_email(raw_email: str) -> dict:
    """Extract sender, subject, and body from a raw email blob."""
    if not raw_email or not raw_email.strip():
        return {"status": "error", "error": "raw_email is required."}
    sender = ""
    subject = ""
    for line in raw_email.splitlines()[:10]:
        m = re.match(r"^From:\s*(.+)$", line, re.IGNORECASE)
        if m:
            sender = m.group(1).strip()
        m = re.match(r"^Subject:\s*(.+)$", line, re.IGNORECASE)
        if m:
            subject = m.group(1).strip()
    body = _strip_headers(raw_email)
    return {
        "status": "ok",
        "from": sender,
        "subject": subject,
        "body_preview": body[:300],
        "body_length": len(body),
    }


def classify_category(subject: str, body: str) -> dict:
    """Return the most likely category for a single email."""
    text = f"{subject}\n{body}".lower()
    scores = {cat: 0 for cat in _CATEGORIES}
    for cat, keywords in _CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] == 0:
        best = ("other", 0)
    return {"status": "ok", "category": best[0], "scores": scores, "top_score": best[1]}


def priority_score(subject: str, body: str) -> dict:
    """Return a 0-100 priority score (urgency, action verbs, length)."""
    text = f"{subject}\n{body}"
    score = 0
    score += 25 * len(_URGENT_RE.findall(text))
    score += 15 if "?" in text else 0
    score += 10 if re.search(r"\bplease\b", text, re.IGNORECASE) else 0
    score += 5 if re.search(r"\b(review|approve|sign|reply)\b", text, re.IGNORECASE) else 0
    score -= 5 if re.search(r"^(re:|fwd:)", subject, re.IGNORECASE) else 0
    score = max(0, min(100, score))
    label = "high" if score >= 50 else "medium" if score >= 20 else "low"
    return {"status": "ok", "score": score, "priority": label}


def extract_action_items(body: str) -> dict:
    """Pull candidate action items from a body (lines starting with verbs)."""
    VERBS = ("send", "review", "reply", "schedule", "submit", "approve",
             "sign", "call", "update", "prepare", "draft", "confirm",
             "follow up", "share", "complete", "deliver")
    items: List[str] = []
    for line in body.splitlines():
        s = line.strip("-*• \t")
        low = s.lower()
        if not s:
            continue
        if any(low.startswith(v) for v in VERBS):
            items.append(s)
    return {"status": "ok", "items": items, "count": len(items)}


def batch_triage(emails_json: str) -> dict:
    """Triage a JSON list of email objects and return a priority-sorted list.

    Each input item: ``{"from": str, "subject": str, "body": str}``
    Each output item adds ``category``, ``priority``, ``score``,
    ``action_items``.
    """
    try:
        emails = json.loads(emails_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    if not isinstance(emails, list):
        return {"status": "error", "error": "expected a JSON list."}
    out = []
    for e in emails:
        subj = e.get("subject", "")
        body = e.get("body", "")
        cat = classify_category(subj, body).get("category", "other")
        pri = priority_score(subj, body)
        acts = extract_action_items(body).get("items", [])
        out.append({
            "from": e.get("from", ""),
            "subject": subj,
            "category": cat,
            "priority": pri.get("priority", "low"),
            "score": pri.get("score", 0),
            "action_items": acts,
        })
    out.sort(key=lambda r: r["score"], reverse=True)
    summary = dict(Counter(r["category"] for r in out))
    return {"status": "ok", "count": len(out), "by_category": summary, "items": out}


root_agent = Agent(
    name="email_classifier_agent",
    model="gemini-2.0-flash",
    description=(
        "Triages an inbox: classifies each email by category and "
        "priority, extracts action items, and drafts replies."
    ),
    instruction="""
    You are an executive-assistant inbox triage agent.

    WORKFLOW:
    1. If the user pastes a single email, call `parse_email` then
       `classify_category`, `priority_score`, `extract_action_items`,
       and finally draft a short reply.
    2. If the user pastes a JSON list of emails, call `batch_triage`
       to produce a priority-sorted summary.
    3. Always present the final view in two sections:
         a) High-priority items needing action today.
         b) Everything else, grouped by category.
    4. For any high-priority item, draft a 1-3 sentence reply.

    RULES:
    - Never classify based on the sender's identity alone.
    - Reject obvious spam categorisation unless the score is high.
    - Replies should be polite, concise and not invent facts.
    """,
    tools=[
        parse_email, classify_category, priority_score,
        extract_action_items, batch_triage,
    ],
    output_schema=EmailClass,
    output_key="email_classification",
)
