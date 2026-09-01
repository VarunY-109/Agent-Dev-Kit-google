# Email Classifier Agent

A pure-Python ADK agent that triages an inbox. Classifies each email
by category (work / personal / finance / support / newsletter /
spam), scores priority, extracts action items, and (for
high-priority items) drafts a short reply.

## Tools

| Tool | Purpose |
| --- | --- |
| `parse_email(raw)` | Strip headers, return sender/subject/body. |
| `classify_category(subject, body)` | Most-likely category + scores. |
| `priority_score(subject, body)` | 0-100 urgency score. |
| `extract_action_items(body)` | Pull verb-led action lines. |
| `batch_triage(emails_json)` | Triage a JSON list, return sorted. |

## Project Structure

```
31-email-classifier/
└── email_classifier_agent/
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

- "Triage this email: ..."
- "Classify and prioritise these 5 emails: [json list]"
- "Draft a reply to the urgent one."
