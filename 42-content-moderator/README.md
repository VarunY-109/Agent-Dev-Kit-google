# Content Moderator Agent

A pure-Python ADK agent that runs **three independent moderation
signals** (toxicity, PII, policy keywords) and combines them into
a 0-100 risk score with an `approve / review / block` action.

## Tools

| Tool | Purpose |
| --- | --- |
| `detect_toxicity(text)` | Lexicon-based toxic phrase matcher. |
| `detect_pii(text)` | Email, phone, SSN, credit-card, IPv4. |
| `detect_policy(text)` | violence / sexual / drugs / self-harm / spam. |
| `redact(text, pii_json)` | Replace PII spans with category tags. |
| `risk_score(tox, pii, policy)` | 0-100 composite. |
| `moderate(text)` | One-call pipeline. |

## Scoring

| Signal | Per-hit weight |
| --- | --- |
| toxicity | 8 |
| pii | 12 |
| policy keyword | 15 |

| Score | Action |
| --- | --- |
| >= 60 | `block` |
| 25-59 | `review` |
| < 25 | `approve` |

## Project Structure

```
42-content-moderator/
└── content_moderator_agent/
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

## Caveat

This is a **demo** signal layer. For production moderation, layer
this with a hosted classifier (e.g. Perspective API, OpenAI
Moderation) and a human-review queue.
