"""Quiz Master Agent.

Adaptive quiz generator with a tiny Leitner-system spaced-repetition
engine. The agent picks the next question based on per-card recall
stats.
"""

import json
import random
import time
from typing import Dict, List

from google.adk.agents import Agent
from google.adk.tools import ToolContext


_LEITNER_BOXES = 5
_PROGRESS_KEY = "quiz_progress"


def _default_state() -> Dict:
    return {"history": {}, "box": {}}


def _state(ctx: ToolContext) -> Dict:
    s = getattr(ctx, "state", None)
    if s is None:
        raise RuntimeError("ToolContext.state unavailable.")
    if _PROGRESS_KEY not in s:
        s[_PROGRESS_KEY] = _default_state()
    return s[_PROGRESS_KEY]


_BANK = {
    "general": [
        {"q": "What is the capital of France?",
         "choices": ["Berlin", "Paris", "Madrid", "Rome"],
         "answer": 1, "explanation": "Paris has been the capital since 987 AD."},
        {"q": "How many planets are in our solar system?",
         "choices": ["7", "8", "9", "12"],
         "answer": 1, "explanation": "Pluto was reclassified in 2006."},
        {"q": "What does HTTP stand for?",
         "choices": ["HyperText Transfer Protocol",
                     "High Throughput Text Pipeline",
                     "Host-To-Host Transfer Process",
                     "Hyperlink Transit Type Program"],
         "answer": 0, "explanation": "Defined in RFC 2616 / RFC 9110."},
    ],
    "python": [
        {"q": "Which keyword defines an async function in Python?",
         "choices": ["def", "async", "await", "lambda"],
         "answer": 1, "explanation": "`async def` declares a coroutine."},
        {"q": "What does `len([])` return?",
         "choices": ["0", "1", "None", "Error"],
         "answer": 0, "explanation": "Empty containers have length 0."},
        {"q": "Which module parses JSON in the stdlib?",
         "choices": ["pickle", "json", "csv", "ast"],
         "answer": 1, "explanation": "`import json`."},
    ],
}


def list_topics() -> dict:
    """Return the available quiz topics."""
    return {"status": "ok", "topics": sorted(_BANK.keys())}


def next_question(ctx: ToolContext, topic: str = "general") -> dict:
    """Pick the next question, weighted toward lower Leitner boxes.

    Cards in box 0 (worst recall) are 5x more likely to be drawn
    than cards in box 4 (best recall).
    """
    state = _state(ctx)
    bank = _BANK.get(topic)
    if not bank:
        return {"status": "error", "error": f"unknown topic: {topic!r}"}
    boxes = state["box"]
    weights: List[int] = []
    pool: List[Dict] = []
    for i, card in enumerate(bank):
        b = boxes.get(str(i), 0)
        weights.append(_LEITNER_BOXES - b)
        pool.append(card)
    if sum(weights) == 0:
        idx = random.randrange(len(pool))
    else:
        idx = random.choices(range(len(pool)), weights=weights, k=1)[0]
    card = pool[idx]
    return {
        "status": "ok",
        "index": idx,
        "question": card["q"],
        "choices": card["choices"],
    }


def grade(ctx: ToolContext, index: int, chosen: int) -> dict:
    """Grade the user's answer and update the Leitner box.

    Correct -> box + 1 (capped). Wrong -> box 0.
    """
    state = _state(ctx)
    boxes = state["box"]
    history = state["history"]
    key = str(index)
    current = boxes.get(key, 0)
    flat = [c for topic in _BANK.values() for c in topic]
    if index < 0 or index >= len(flat):
        return {"status": "error", "error": "index out of range."}
    card = flat[index]
    correct = chosen == card["answer"]
    if correct:
        new_box = min(_LEITNER_BOXES - 1, current + 1)
    else:
        new_box = 0
    boxes[key] = new_box
    h = history.setdefault(key, {"correct": 0, "wrong": 0, "seen": 0})
    h["seen"] += 1
    if correct:
        h["correct"] += 1
    else:
        h["wrong"] += 1
    return {
        "status": "ok",
        "correct": correct,
        "new_box": new_box,
        "explanation": card.get("explanation", ""),
        "stats": h,
    }


def progress(ctx: ToolContext) -> dict:
    """Return the current Leitner box distribution and per-card stats."""
    state = _state(ctx)
    box_dist = [0] * _LEITNER_BOXES
    for v in state["box"].values():
        if 0 <= v < _LEITNER_BOXES:
            box_dist[v] += 1
    total_seen = sum(h["seen"] for h in state["history"].values())
    total_correct = sum(h["correct"] for h in state["history"].values())
    accuracy = round(100 * total_correct / total_seen, 1) if total_seen else 0.0
    return {
        "status": "ok",
        "box_distribution": box_dist,
        "cards_seen": total_seen,
        "accuracy_pct": accuracy,
    }


def reset_progress(ctx: ToolContext) -> dict:
    """Reset the per-session Leitner state."""
    state = _state(ctx)
    state["box"].clear()
    state["history"].clear()
    return {"status": "ok", "reset": True}


def now_ms() -> dict:
    """Current epoch in milliseconds (useful for response-time stats)."""
    return {"status": "ok", "now_ms": int(time.time() * 1000)}


root_agent = Agent(
    name="quiz_master_agent",
    model="gemini-2.0-flash",
    description=(
        "Adaptive quiz master using a Leitner-system spaced-repetition "
        "engine to schedule the next question per topic."
    ),
    instruction="""
    You are a supportive, encouraging quiz master.

    WORKFLOW for each turn:
    1. Call `list_topics` if the user hasn't picked one yet.
    2. Call `next_question` to get the question and choices.
    3. Wait for the user's answer, then call `grade` to score it
       and update the Leitner box.
    4. Use the `explanation` returned by `grade` to teach the
       concept; if the user was wrong, also offer a mnemonic.
    5. After 5 questions, call `progress` and summarise the user's
       box distribution and accuracy.

    RULES:
    - Never reveal the answer before the user has responded.
    - If the user asks for a "hard" round, weight selection toward
       higher boxes.
    - If accuracy drops below 50% over 10 questions, suggest
       reviewing the topic fundamentals before continuing.
    """,
    tools=[
        list_topics, next_question, grade, progress,
        reset_progress, now_ms,
    ],
)
