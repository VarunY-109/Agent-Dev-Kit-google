# System Incident Triage Agent

A pure-Python ADK agent that triages a log dump, clusters lines by
fingerprint, matches against a built-in runbook library, and
returns a root-cause hypothesis with confidence.

## Tools

| Tool | Purpose |
| --- | --- |
| `parse_logs(text)` | Cluster by fingerprint, return cluster table. |
| `classify_signature(signature)` | Map a log line to a runbook category. |
| `runbook(category)` | Fetch runbook steps. |
| `triage(text)` | One-call pipeline. |

## Runbook Categories

| Category | Fingerprint examples |
| --- | --- |
| database | "connection refused", "deadlock detected" |
| memory | "out of memory", "OOMKilled" |
| auth | "invalid token", "401" |
| network | "DNS timeout", "no route to host" |
| deploy | "recent deploy", "migration failed" |
| unknown | Falls through; needs human investigation |

## Project Structure

```
44-system-incident/
└── system_incident_agent/
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

- "Triage this error log: ..."
- "What runbook applies to a 'connection refused' signature?"
- "Cluster my 500 lines and tell me the dominant fingerprint."
