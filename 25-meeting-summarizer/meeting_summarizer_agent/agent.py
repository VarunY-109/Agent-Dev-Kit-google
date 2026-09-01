"""Meeting Summarizer Agent.

A multi-step agent that takes a raw meeting transcript (or free-form
notes) and produces a structured meeting record: title, attendees,
decisions, action items with owners and due dates, parking-lot
items, and a one-paragraph executive summary.
"""

import json
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    task: str = Field(description="The concrete next step.")
    owner: str = Field(description="Person responsible, or 'Unassigned'.")
    due: str = Field(description="ISO date (YYYY-MM-DD) or 'TBD'.")


class MeetingRecord(BaseModel):
    title: str
    date: str
    attendees: List[str]
    executive_summary: str
    decisions: List[str]
    action_items: List[ActionItem]
    parking_lot: List[str]
    key_quotes: List[str]


_SPEAKER_RE = re.compile(r"^\s*([A-Z][A-Za-z .'-]{1,40}):\s*(.*)$")
_VERB_HINTS = (
    "will ", "should ", "need to ", "let's ", "lets ", "by next",
    "by friday", "by monday", "by tuesday", "by wednesday",
    "by thursday", "by the ", "follow up", "action:", "todo:",
    "to-do", "[ai]", "i'll ", "i will ", "we'll ", "we will ",
)


def _detect_attendees(text: str) -> List[str]:
    speakers = []
    for line in text.splitlines():
        m = _SPEAKER_RE.match(line)
        if m:
            name = m.group(1).strip()
            if name not in speakers:
                speakers.append(name)
    return speakers


def _detect_action_lines(text: str) -> List[str]:
    out: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        if any(h in low for h in _VERB_HINTS):
            out.append(line)
    return out


def _extract_dates(text: str) -> List[str]:
    found = []
    for pattern in (
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    ):
        for m in re.findall(pattern, text):
            found.append(m)
    return sorted(set(found))


def parse_transcript(text: str) -> dict:
    """Parse a raw transcript into structural hints.

    Returns detected speakers, candidate action-item lines, and any
    explicit dates mentioned in the text.
    """
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    return {
        "status": "ok",
        "char_count": len(text),
        "line_count": len(text.splitlines()),
        "speakers": _detect_attendees(text),
        "action_line_candidates": _detect_action_lines(text),
        "dates_mentioned": _extract_dates(text),
    }


def word_frequency(text: str, top_n: int = 10) -> dict:
    """Return the most common meaningful words in the text."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "so", "of", "to", "in",
        "on", "for", "with", "is", "are", "was", "were", "be", "been",
        "being", "this", "that", "these", "those", "it", "its", "i",
        "we", "you", "they", "he", "she", "as", "at", "by", "from",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "should", "may", "might", "not", "no", "yes",
        "if", "then", "than", "also", "just", "very", "really",
    }
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.lower())
    counts = Counter(w for w in words if w not in STOPWORDS)
    return {
        "status": "ok",
        "top_words": [{"word": w, "count": c} for w, c in counts.most_common(top_n)],
    }


def diff_summaries(prev: str, curr: str) -> dict:
    """Compare two meeting summaries and surface what changed."""
    if not prev or not curr:
        return {"status": "error", "error": "Both prev and curr are required."}
    prev_words = set(re.findall(r"[A-Za-z]{4,}", prev.lower()))
    curr_words = set(re.findall(r"[A-Za-z]{4,}", curr.lower()))
    return {
        "status": "ok",
        "added": sorted(curr_words - prev_words)[:30],
        "removed": sorted(prev_words - curr_words)[:30],
        "shared_count": len(prev_words & curr_words),
    }


def now_iso() -> dict:
    """Return the current UTC timestamp in ISO format."""
    return {"status": "ok", "iso": datetime.utcnow().isoformat(timespec="seconds") + "Z"}


root_agent = Agent(
    name="meeting_summarizer_agent",
    model="gemini-2.0-flash",
    description=(
        "Parses a raw meeting transcript into a structured record "
        "with attendees, decisions, action items and a summary."
    ),
    instruction="""
    You are an expert meeting-summarisation assistant.

    WORKFLOW:
    1. When the user pastes a transcript or notes, call
       `parse_transcript` to detect speakers, action lines and dates.
    2. Optionally call `word_frequency` to surface the dominant
       topics of the meeting.
    3. Produce a JSON object that EXACTLY matches this Pydantic
       schema (no extra keys, no prose outside the JSON):
         {
           "title": "string",
           "date": "YYYY-MM-DD or 'unknown'",
           "attendees": ["name1", ...],
           "executive_summary": "1-3 sentence TL;DR",
           "decisions": ["decision 1", ...],
           "action_items": [
             {"task": "...", "owner": "...", "due": "YYYY-MM-DD or TBD"}
           ],
           "parking_lot": ["deferred topic 1", ...],
           "key_quotes": ["verbatim quote 1", ...]
         }
    4. Use the structural hints from the tools to inform owners and
       dates; if a date is vague (e.g. "next Friday"), set
       due = "TBD" rather than guess.
    5. After producing the JSON, present the executive summary and
       action items as bullet points for quick reading.

    RULES:
    - Never invent attendees. Only list names returned by
       `parse_transcript` or explicitly named in the user's text.
    - If the transcript is empty or too short, ask for clarification.
    - Action items must be SMART (specific, assigned, time-bounded).
    """,
    tools=[parse_transcript, word_frequency, diff_summaries, now_iso],
    output_schema=MeetingRecord,
    output_key="meeting_record",
)
