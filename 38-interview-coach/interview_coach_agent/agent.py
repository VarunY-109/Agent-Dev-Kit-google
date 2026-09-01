"""Interview Coach Agent.

Conducts a mock interview for a given role. Asks questions from a
role-specific bank, scores answers against a rubric, and produces
an end-of-session report card.
"""

import json
import re
from typing import Dict, List

from google.adk.agents import Agent
from google.adk.tools import ToolContext


_SESSION_KEY = "interview_session"


_BANK = {
    "software engineer": [
        {"q": "Walk me through how you'd design a URL shortener.",
         "rubric": ["data model", "hashing", "scale", "caching"]},
        {"q": "Describe a time you had to debug a production issue.",
         "rubric": ["incident", "diagnosis", "fix", "prevention"]},
        {"q": "How do you handle disagreement with a tech lead?",
         "rubric": ["empathy", "evidence", "compromise", "outcome"]},
        {"q": "What's the trade-off between SQL and NoSQL?",
         "rubric": ["schema", "consistency", "scale", "use case"]},
    ],
    "product manager": [
        {"q": "How would you prioritise a backlog of 50 feature requests?",
         "rubric": ["impact", "effort", "framework", "stakeholders"]},
        {"q": "Tell me about a launch that failed.",
         "rubric": ["context", "cause", "response", "learning"]},
        {"q": "How do you measure the success of a new feature?",
         "rubric": ["metric", "baseline", "counter-metric", "review"]},
    ],
    "data scientist": [
        {"q": "Explain selection bias to a non-technical stakeholder.",
         "rubric": ["example", "impact", "mitigation", "clarity"]},
        {"q": "How do you handle class imbalance?",
         "rubric": ["metric choice", "resampling", "cost-sensitive", "validation"]},
    ],
}


def list_roles() -> dict:
    """Available mock-interview roles."""
    return {"status": "ok", "roles": sorted(_BANK.keys())}


def start_session(ctx: ToolContext, role: str) -> dict:
    """Start a fresh interview session for ``role``."""
    if role not in _BANK:
        return {"status": "error", "error": f"unknown role: {role!r}"}
    state = getattr(ctx, "state", None)
    if state is None:
        return {"status": "error", "error": "ToolContext.state unavailable."}
    state[_SESSION_KEY] = {
        "role": role,
        "index": 0,
        "answers": [],
        "scores": [],
    }
    q = _BANK[role][0]
    return {
        "status": "ok",
        "role": role,
        "index": 0,
        "total": len(_BANK[role]),
        "question": q["q"],
        "rubric": q["rubric"],
    }


def current_question(ctx: ToolContext) -> dict:
    """Return the current question (or finish signal if done)."""
    state = getattr(ctx, "state", None)
    sess = state.get(_SESSION_KEY) if state else None
    if not sess:
        return {"status": "error", "error": "no active session."}
    bank = _BANK[sess["role"]]
    i = sess["index"]
    if i >= len(bank):
        return {"status": "ok", "done": True, "index": i, "total": len(bank)}
    q = bank[i]
    return {
        "status": "ok",
        "done": False,
        "index": i,
        "total": len(bank),
        "question": q["q"],
        "rubric": q["rubric"],
    }


def submit_answer(ctx: ToolContext, answer: str) -> dict:
    """Score the current answer against the rubric and advance."""
    state = getattr(ctx, "state", None)
    sess = state.get(_SESSION_KEY) if state else None
    if not sess:
        return {"status": "error", "error": "no active session."}
    bank = _BANK[sess["role"]]
    i = sess["index"]
    if i >= len(bank):
        return {"status": "error", "error": "session already complete."}
    q = bank[i]
    low = answer.lower()
    matched = [r for r in q["rubric"] if any(part in low for part in _parts(r))]
    score = round(100 * len(matched) / max(1, len(q["rubric"])))
    missing = [r for r in q["rubric"] if r not in matched]
    sess["answers"].append(answer)
    sess["scores"].append({
        "question": q["q"],
        "score": score,
        "matched": matched,
        "missing": missing,
    })
    sess["index"] += 1
    nxt = bank[sess["index"]] if sess["index"] < len(bank) else None
    return {
        "status": "ok",
        "score": score,
        "matched": matched,
        "missing": missing,
        "index": sess["index"],
        "done": nxt is None,
        "next_question": nxt["q"] if nxt else None,
        "next_rubric": nxt["rubric"] if nxt else [],
    }


def _parts(rubric: str) -> List[str]:
    base = rubric.lower()
    parts = [base]
    for kw in base.split():
        if len(kw) > 3:
            parts.append(kw)
    return parts


def session_report(ctx: ToolContext) -> dict:
    """Compute a per-question and overall report card."""
    state = getattr(ctx, "state", None)
    sess = state.get(_SESSION_KEY) if state else None
    if not sess:
        return {"status": "error", "error": "no active session."}
    scores = sess["scores"]
    overall = round(sum(s["score"] for s in scores) / max(1, len(scores)), 1)
    label = "strong" if overall >= 80 else "ok" if overall >= 60 else "needs work"
    strengths, gaps = [], []
    for s in scores:
        for m in s["matched"]:
            strengths.append(m)
        for m in s["missing"]:
            gaps.append(m)
    from collections import Counter
    return {
        "status": "ok",
        "role": sess["role"],
        "question_count": len(scores),
        "overall_score": overall,
        "label": label,
        "strengths": [k for k, _ in Counter(strengths).most_common(5)],
        "gaps": [k for k, _ in Counter(gaps).most_common(5)],
        "per_question": scores,
    }


root_agent = Agent(
    name="interview_coach_agent",
    model="gemini-2.0-flash",
    description=(
        "Conducts a mock interview for a chosen role, scoring "
        "answers against a rubric and producing a report card."
    ),
    instruction="""
    You are a supportive, structured interview coach.

    WORKFLOW for every session:
    1. Ask the user to pick a role (or call `list_roles` to show
       the available list).
    2. Call `start_session` to initialise the per-session state.
    3. Use `current_question` to fetch the active question and
       rubric. Tell the user the question and the rubric criteria
       that will be used for scoring.
    4. Wait for their answer, then call `submit_answer`.
    5. Briefly tell them what they hit and what they missed.
    6. Repeat until `done=True`, then call `session_report` and
       present:
         * Overall score and label.
         * Top 3 strengths and top 3 gaps.
         * 3 specific follow-up questions they should rehearse.

    RULES:
    - Never reveal the rubric before they answer.
    - If the user's answer is < 30 words, ask them to expand
       before scoring.
    - Keep tone encouraging; critique substance, never style.
    """,
    tools=[
        list_roles, start_session, current_question,
        submit_answer, session_report,
    ],
)
