# Meeting Summarizer Agent

A pure-Python ADK agent that converts a raw meeting transcript (or
free-form notes) into a **structured, validated** meeting record
with attendees, decisions, action items (with owners & due dates),
parking-lot items, and an executive summary.

## Tools

| Tool | Purpose |
| --- | --- |
| `parse_transcript(text)` | Detect speakers, candidate action lines, mentioned dates. |
| `word_frequency(text, top_n=10)` | Surface the dominant topics. |
| `diff_summaries(prev, curr)` | Compare two drafts and surface what changed. |
| `now_iso()` | Return the current UTC timestamp. |

## Output Schema

The agent is configured with `output_schema=MeetingRecord`, so its
final reply is guaranteed to be valid JSON shaped like:

```json
{
  "title": "Q3 Roadmap Sync",
  "date": "2026-08-21",
  "attendees": ["Alice", "Bob"],
  "executive_summary": "...",
  "decisions": ["Ship feature X in v2.1", "..."],
  "action_items": [
    {"task": "Draft RFC for X", "owner": "Bob", "due": "2026-08-28"}
  ],
  "parking_lot": ["Pricing model discussion"],
  "key_quotes": ["..."]
}
```

## Project Structure

```
25-meeting-summarizer/
└── meeting_summarizer_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env       # set GOOGLE_API_KEY
adk web
```

Select `meeting_summarizer_agent` and paste a transcript.
