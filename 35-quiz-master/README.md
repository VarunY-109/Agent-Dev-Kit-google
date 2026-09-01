# Quiz Master Agent

A pure-Python ADK agent that runs an **adaptive quiz** with a tiny
**Leitner-system** spaced-repetition engine. Cards answered
correctly move to higher boxes (reviewed less often); cards
answered wrongly drop back to box 0.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_topics()` | Available topic names. |
| `next_question(ctx, topic)` | Pick a question weighted by box. |
| `grade(ctx, index, chosen)` | Score, update box, return explanation. |
| `progress(ctx)` | Box distribution + accuracy. |
| `reset_progress(ctx)` | Wipe per-session state. |
| `now_ms()` | Epoch ms (for response-time stats). |

## Leitner Math

The next-question picker weights each card by `5 - current_box`, so
a card in **box 0** is **5x more likely** to be drawn than a card
in **box 4**. Correct answers move a card up by 1 box; wrong
answers reset it to 0.

## Project Structure

```
35-quiz-master/
└── quiz_master_agent/
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

- "Start a python quiz."
- "Give me a general knowledge round."
- "How am I doing so far?"
- "Reset and switch to a hard python round."
