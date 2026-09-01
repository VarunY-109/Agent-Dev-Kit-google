# Interview Coach Agent

A pure-Python ADK agent that runs a **mock interview** for a chosen
role, scores each answer against a per-question rubric, and
produces an end-of-session report card.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_roles()` | Available roles. |
| `start_session(ctx, role)` | Initialise per-session state. |
| `current_question(ctx)` | Active question + rubric. |
| `submit_answer(ctx, answer)` | Score, advance. |
| `session_report(ctx)` | Overall score, strengths, gaps. |

## Rubric Scoring

Each question has a list of rubric keywords. The agent scores the
answer as `100 * matched_keywords / total_rubric_keywords`.

## Project Structure

```
38-interview-coach/
└── interview_coach_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env
adk web
```

## Example Prompts

- "Start a mock interview for a software engineer role."
- "How did I do overall?"
- "Give me 3 follow-up questions to rehearse based on my gaps."
